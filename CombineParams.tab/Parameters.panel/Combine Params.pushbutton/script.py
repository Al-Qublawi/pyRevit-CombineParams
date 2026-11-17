# -*- coding: utf-8 -*-
"""Combine the values of two parameters into a third parameter,
with a custom separator, for elements of a chosen category."""

__title__ = "Combine\nParams"
__author__ = "Claude"

from pyrevit import revit, DB, forms, script

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

SCOPE_MODEL = "Whole Model"
SCOPE_VIEW = "Active View"
SCOPE_SEL = "Current Selection"


# ---------------------------------------------------------------- helpers
def get_type(el):
    try:
        tid = el.GetTypeId()
        if tid and tid != DB.ElementId.InvalidElementId:
            return doc.GetElement(tid)
    except Exception:
        pass
    return None


def param_value(p):
    """Return the parameter value as display text ('' if empty)."""
    if p is None or not p.HasValue:
        return ""
    st = p.StorageType
    val = None
    if st == DB.StorageType.String:
        val = p.AsString()
    elif st == DB.StorageType.ElementId:
        val = p.AsValueString()
        if not val:
            eid = p.AsElementId()
            if eid and eid != DB.ElementId.InvalidElementId:
                ref = doc.GetElement(eid)
                if ref is not None:
                    val = getattr(ref, "Name", None)
    else:
        val = p.AsValueString()
        if val is None:
            if st == DB.StorageType.Integer:
                val = str(p.AsInteger())
            elif st == DB.StorageType.Double:
                val = str(p.AsDouble())
    return (val or "").strip()


def get_value(el, name):
    """Instance parameter first, then type parameter."""
    p = el.LookupParameter(name)
    if p is not None:
        return param_value(p)
    t = get_type(el)
    if t is not None:
        return param_value(t.LookupParameter(name))
    return ""


def collect_elements(cat_id, scope):
    if scope == SCOPE_SEL:
        els = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
        return [e for e in els if e is not None and e.Category is not None
                and e.Category.Id == cat_id]
    if scope == SCOPE_VIEW:
        col = DB.FilteredElementCollector(doc, doc.ActiveView.Id)
    else:
        col = DB.FilteredElementCollector(doc)
    return list(col.OfCategoryId(cat_id).WhereElementIsNotElementType())


# ------------------------------------------------------------- 1. category
cats = {}
for el in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
    c = el.Category
    if c is not None and c.Name and c.Name not in cats:
        cats[c.Name] = c.Id

if not cats:
    forms.alert("No categories with elements found.", exitscript=True)

cat_names = forms.SelectFromList.show(sorted(cats.keys()),
                                      title="1) Select Categories (one or more)",
                                      multiselect=True)
if not cat_names:
    script.exit()
cat_name = ", ".join(cat_names)

# ---------------------------------------------------------------- 2. scope
scope = forms.CommandSwitchWindow.show([SCOPE_MODEL, SCOPE_VIEW, SCOPE_SEL],
                                       message="2) Apply to:")
if not scope:
    script.exit()

elements = []
sample = []   # a few elements of every category, used to list parameters
for cn in cat_names:
    cat_els = collect_elements(cats[cn], scope)
    elements.extend(cat_els)
    sample.extend(cat_els[:300])
if not elements:
    forms.alert("No elements of [{}] found in: {}".format(cat_name, scope),
                exitscript=True)

# ------------------------------------------------- 3. gather parameter names
source_names = set()
target_opts = {}   # display -> (name, is_type)
types_seen = set()
for el in sample:
    for p in el.Parameters:
        n = p.Definition.Name
        source_names.add(n)
        if p.StorageType == DB.StorageType.String and not p.IsReadOnly:
            target_opts["{}  [Instance]".format(n)] = (n, False)
    t = get_type(el)
    if t is not None and t.Id not in types_seen:
        types_seen.add(t.Id)
        for p in t.Parameters:
            n = p.Definition.Name
            source_names.add(n)
            if p.StorageType == DB.StorageType.String and not p.IsReadOnly:
                key = "{}  [Type]".format(n)
                if "{}  [Instance]".format(n) not in target_opts:
                    target_opts[key] = (n, True)

source_names = sorted(source_names)

p1 = forms.SelectFromList.show(source_names, title="3) First Parameter",
                               multiselect=False)
if not p1:
    script.exit()
p2 = forms.SelectFromList.show(source_names, title="4) Second Parameter",
                               multiselect=False)
if not p2:
    script.exit()

if not target_opts:
    forms.alert("No writable text parameters found on these elements.",
                exitscript=True)
tgt_key = forms.SelectFromList.show(sorted(target_opts.keys()),
                                    title="5) Target Parameter (text)",
                                    multiselect=False)
if not tgt_key:
    script.exit()
tgt_name, tgt_is_type = target_opts[tgt_key]

sep = forms.ask_for_string(default=".", prompt="6) Separator between values:",
                           title="Separator")
if sep is None:
    script.exit()

# ------------------------------------------------------------------ 5. run
done, skipped_empty, failed, conflicts = 0, 0, 0, 0
type_values = {}   # type id -> value already written
fail_ids = []

with revit.Transaction("Combine Parameters"):
    for el in elements:
        vals = [v for v in (get_value(el, p1), get_value(el, p2)) if v]
        if not vals:
            skipped_empty += 1
            continue
        new_val = sep.join(vals)
        try:
            if tgt_is_type:
                t = get_type(el)
                if t is None:
                    failed += 1
                    continue
                key = t.Id
                if key in type_values:
                    if type_values[key] != new_val:
                        conflicts += 1
                    continue
                tp = t.LookupParameter(tgt_name)
                if tp is None or tp.IsReadOnly:
                    failed += 1
                    continue
                tp.Set(new_val)
                type_values[key] = new_val
                done += 1
            else:
                tp = el.LookupParameter(tgt_name)
                if tp is None or tp.IsReadOnly:
                    failed += 1
                    fail_ids.append(el.Id)
                    continue
                tp.Set(new_val)
                done += 1
        except Exception:
            failed += 1
            fail_ids.append(el.Id)

# --------------------------------------------------------------- 6. report
output.print_md("## Combine Parameters")
output.print_md("**Categories:** {}  |**Scope:** {}  |  **Elements:** {}".format(
    cat_name, scope, len(elements)))
output.print_md("**Formula:** `{}` + `{}` + `{}` -> **{}**".format(
    p1, sep, p2, tgt_key))
output.print_md("- Updated: **{}** {}".format(
    done, "types" if tgt_is_type else "elements"))
output.print_md("- Skipped (both values empty): {}".format(skipped_empty))
output.print_md("- Failed / read-only: {}".format(failed))
if tgt_is_type and conflicts:
    output.print_md("- WARNING: {} elements share a type but had different values "
                    "(first value kept).".format(conflicts))
if fail_ids:
    output.print_md("Failed elements: " + " ".join(
        output.linkify(i) for i in fail_ids[:100]))
