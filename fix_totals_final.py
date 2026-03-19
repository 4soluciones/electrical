# Final fixes for totals
path = r"templates\buys\buy_list_edit.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove duplicate parseNum line (keep parseDecimal)
if "function parseNum(val)" in content and "function parseDecimal" in content:
    content = content.replace(
        "        function parseNum(val) { if (val === '' || val == null) return 0; let n = parseFloat(String(val).replace(',', '.')); return isNaN(n) ? 0 : n; }\n        function sum_table()",
        "        function sum_table()"
    )
    print("Removed duplicate parseNum")

# 2. Add sum_table() on page load
if "sum_table()" not in content or "sum_table();" not in content.split("$(document).ready")[1].split("});")[0]:
    # Add after check_dollar in document.ready
    old_ready = """        $(document).ready(function () {
            let _check = $("#check_dollar")
            if (_check.is(':checked')) {
                $(".change-money").text('$')
            } else {
                $(".change-money").text('S/')
            }
        });"""
    new_ready = """        $(document).ready(function () {
            let _check = $("#check_dollar")
            if (_check.is(':checked')) {
                $(".change-money").text('$')
            } else {
                $(".change-money").text('S/')
            }
            sum_table();
        });"""
    if old_ready in content:
        content = content.replace(old_ready, new_ready)
        print("Added sum_table on load")
    else:
        print("document.ready block not found for sum_table")

# 3. Fix check-igv change handler to use #check_igv
content = content.replace(
    "$(document).on('change', '#id_detail_data_grid tfoot tr input.check-igv'",
    "$(document).on('change', '#check_igv'"
)
print("Fixed check-igv handler")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
