# CombineParams – pyRevit Extension

بيجمع قيم 2 باراميتر في باراميتر تالت، وبينهم فاصل انت بتختاره، على كاتيجوري واحدة أو أكتر.

## التركيب (مرة واحدة)
لازم يكون [pyRevit](https://github.com/pyrevitlabs/pyRevit/releases) متسطب. افتح Command Prompt وشغل:

```
pyrevit extend ui CombineParams https://github.com/Al-Qublawi/pyRevit-CombineParams.git
```

بعدها افتح Revit، أو اعمل **pyRevit ← Reload** لو Revit مفتوح. هيظهرلك تاب اسمه **CombineParams**.

## التحديث
```
pyrevit extensions update CombineParams
```
وبعدين **pyRevit ← Reload**.

## طريقة الاستخدام
1. اختار كاتيجوري واحدة أو أكتر.
2. اختار النطاق: Whole Model أو Active View أو Current Selection.
3. اختار الباراميتر الأول والتاني (Instance أو Type).
4. اختار الباراميتر الهدف (لازم يكون Text).
5. اكتب الفاصل، والافتراضي `.`.

- لو باراميتر فاضي بيتجاهل، ولو الاتنين فاضيين العنصر بيتساب.
- العملية كلها بتتعمل في Transaction واحدة، فتقدر ترجع فيها بـ Ctrl+Z.

## إلغاء التركيب
```
pyrevit extend remove CombineParams
```
