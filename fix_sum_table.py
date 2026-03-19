# Fix sum_table and calculate_total
path = r"templates\buys\buy_list_edit.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Improve sum_table: robust parsing + use #id_detail_data_foot for footer
old_sum = """        function sum_table() {
            let igv = 0;
            let base = 0;
            let sum_total = 0;
            let total_freight = 0;
            let total_document = 0;
            let _total;

            {#total_freight = Number($("#id_freight_data_grid tbody#details-freight tr td.total-freight input#id_total_freight").val());#}

            $("#id_detail_data_grid tbody#details-table tr.item-row").each(function () {
                let td_total = Number(($(this).find("td.total-row input.total-detail").val() || '0').replace(',', '.'));
                sum_total = sum_total + td_total
            });

            let _check_igv = $("#id_detail_data_grid tfoot tr input.check-igv")

            if (_check_igv.is(':checked')) {
                base = sum_total / 1.18
                igv = sum_total - base
                _total = base + igv
                total_document = _total + total_freight

            } else {
                base = sum_total
                igv = sum_total * 0.18
                _total = base + igv
                total_document = _total + total_freight
            }

            $("#id_detail_data_grid tfoot tr input.total-foot-base").val(base.toFixed(2));
            $("#id_detail_data_grid tfoot tr input.total-foot-igv").val(igv.toFixed(2));
            $("#id_detail_data_grid tfoot tr input.total-foot-total").val(_total.toFixed(2));
            {#$("#id_detail_data_grid tfoot tr input.total-foot-freight").val(total_freight.toFixed(2));#}
            $("#id_detail_data_grid tfoot tr input.total-foot-document").val(total_document.toFixed(2));
        }"""

new_sum = """        function parseNum(val) {
            if (val === '' || val === null || val === undefined) return 0;
            let s = String(val).replace(',', '.').replace(/\\s/g, '');
            let n = parseFloat(s);
            return isNaN(n) ? 0 : n;
        }

        function sum_table() {
            let igv = 0;
            let base = 0;
            let sum_total = 0;
            let total_freight = 0;
            let total_document = 0;
            let _total;

            $("#id_detail_data_grid tbody#details-table tr.item-row").each(function () {
                let val = $(this).find("td.total-row input.total-detail, td.item-total input.total-detail").val();
                sum_total += parseNum(val);
            });

            let $foot = $("#id_detail_data_foot");
            let _check_igv = $foot.length ? $foot.closest("table").siblings("div.form-check").find("input.check-igv") : $("#check_igv");
            if (_check_igv.length === 0) _check_igv = $("#check_igv");

            if (_check_igv.is(':checked')) {
                base = sum_total / 1.18;
                igv = sum_total - base;
                _total = base + igv;
                total_document = _total + total_freight;
            } else {
                base = sum_total;
                igv = sum_total * 0.18;
                _total = base + igv;
                total_document = _total + total_freight;
            }

            $foot.find("input.total-foot-base").val(base.toFixed(2));
            $foot.find("input.total-foot-igv").val(igv.toFixed(2));
            $foot.find("input.total-foot-total").val(_total.toFixed(2));
            $foot.find("input.total-foot-document").val(total_document.toFixed(2));
        }"""

if old_sum in content:
    content = content.replace(old_sum, new_sum)
    print("sum_table fixed OK")
else:
    print("old sum_table NOT FOUND - trying simpler replacement")
    # Simpler: just fix the footer selectors
    content = content.replace(
        '$("#id_detail_data_grid tfoot tr input.total-foot-base").val(base.toFixed(2));',
        '$("#id_detail_data_foot").find("input.total-foot-base").val(base.toFixed(2));'
    )
    content = content.replace(
        '$("#id_detail_data_grid tfoot tr input.total-foot-igv").val(igv.toFixed(2));',
        '$("#id_detail_data_foot").find("input.total-foot-igv").val(igv.toFixed(2));'
    )
    content = content.replace(
        '$("#id_detail_data_grid tfoot tr input.total-foot-total").val(_total.toFixed(2));',
        '$("#id_detail_data_foot").find("input.total-foot-total").val(_total.toFixed(2));'
    )
    content = content.replace(
        '$("#id_detail_data_grid tfoot tr input.total-foot-document").val(total_document.toFixed(2));',
        '$("#id_detail_data_foot").find("input.total-foot-document").val(total_document.toFixed(2));'
    )
    # Add parseNum and fix sum loop
    if 'function parseNum' not in content:
        content = content.replace(
            'function sum_table() {',
            'function parseNum(val) { if (val === \'\' || val == null) return 0; let n = parseFloat(String(val).replace(\',\', \'.\')); return isNaN(n) ? 0 : n; }\n        function sum_table() {'
        )
        content = content.replace(
            'let td_total = Number(($(this).find("td.total-row input.total-detail").val() || \'0\').replace(\',\', \'.\'));',
            'let td_total = parseNum($(this).find("td.total-row input.total-detail, td.item-total input.total-detail").val());'
        )
    print("Applied simpler fixes")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
