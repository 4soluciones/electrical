from django.urls import path
from django.contrib.auth.decorators import login_required

from apps.sales.excels import export_all_products, report_kardex_by_date
from apps.sales.views import *
from apps.sales.views_SUNAT import query_dni
from apps.sales.views_PDF import product_print, print_ticket_order_sales, print_quotation, print_order_bill, print_orders_sales
from apps.sales.views_EXCEL import kardex_glp_excel

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('product_list/', login_required(ProductList.as_view()), name='product_list'),
    path('json_product_create/', login_required(JsonProductCreate.as_view()), name='json_product_create'),
    path('json_product_list/', login_required(JsonProductList.as_view()), name='json_product_list'),
    path('json_product_edit/<int:pk>/',
         login_required(JsonProductUpdate.as_view()), name='json_product_edit'),
    path('get_product/', get_product, name='get_product'),
    path('get_supplies_view/', get_supplies_view, name='get_supplies_view'),
    path('new_quantity_on_hand/', new_quantity_on_hand, name='new_quantity_on_hand'),

    path('get_kardex_by_product/', get_kardex_by_product, name='get_kardex_by_product'),
    path('get_list_kardex/', get_list_kardex, name='get_list_kardex'),

    path('client_list/', login_required(ClientList.as_view()), name='client_list'),

    path('new_client/', new_client, name='new_client'),
    path('get_client/', get_client, name='get_client'),
    path('new_client_associate/', new_client_associate, name='new_client_associate'),

    # path('new_sales/', new_sales, name='new_sales'),

    path('sales_list/', login_required(SalesOrder.as_view()), name='sales_list'),
    path('sales_list/<int:pk>/', login_required(SalesList.as_view()), name='sales_list'),
    path('sales_list/<str:letter>/', login_required(SalesList.as_view()), name='sales_list'),

    path('set_product_detail/', set_product_detail, name='set_product_detail'),
    path('get_product_detail/', get_product_detail, name='get_product_detail'),
    path('update_product_detail/', update_product_detail, name='update_product_detail'),
    path('toogle_status_product_detail/', toogle_status_product_detail,
         name='toogle_status_product_detail'),

    path('get_rate_product/', get_rate_product, name='get_rate_product'),
    # path('create_order_detail/', create_order_detail, name='create_order_detail'),
    path('query_dni/', query_dni, name='query_dni'),

    path('generate_invoice/', generate_invoice, name='generate_invoice'),
    path('get_sales_by_subsidiary_store/', get_sales_by_subsidiary_store,
         name='get_sales_by_subsidiary_store'),
    path('get_products_by_subsidiary/', get_products_by_subsidiary, name='get_products_by_subsidiary'),
    path('toggle_product_enabled/', toggle_product_enabled, name='toggle_product_enabled'),
    path('new_subsidiary_store/', new_subsidiary_store, name='new_subsidiary_store'),
    path('get_recipe/', login_required(get_recipe), name='get_recipe'),
    path('create_recipe/', login_required(create_recipe), name='create_recipe'),
    path('get_manufacture/', login_required(get_manufacture), name='get_manufacture'),
    # path('get_product_recipe/', get_product_recipe, name='get_product_recipe'),
    path('get_unit_by_product/', get_unit_by_product, name='get_unit_by_product'),
    path('get_price_by_product/', get_price_by_product, name='get_price_by_product'),
    path('get_price_and_total_by_product_recipe/', get_price_and_total_by_product_recipe,
         name='get_price_and_total_by_product_recipe'),
    path('get_stock_insume_by_product_recipe/', login_required(get_stock_insume_by_product_recipe),
         name='get_stock_insume_by_product_recipe'),
    path('create_order_manufacture/', login_required(create_order_manufacture),
         name='create_order_manufacture'),
    path('orders_manufacture/', login_required(orders_manufacture), name='orders_manufacture'),
    path('update_manufacture_by_id/', login_required(update_manufacture_by_id),
         name='update_manufacture_by_id'),

    # product get recipe
    path('get_recipe_by_product/', get_recipe_by_product, name='get_recipe_by_product'),

    # ReportLab
    path('product_print/', product_print, name='product_print'),
    path('product_print/<int:pk>/', product_print, name='product_print_one'),
    # path('all_account_order_list_pdf/<int:pk>/', all_account_order_list_pdf, name='all_account_order_list_pdf'),

    # GlP KARDEX
    path('get_kardex_glp/', login_required(get_kardex_glp), name='get_kardex_glp'),
    path('get_only_grid_kardex_glp/<int:pk>/',
         get_only_grid_kardex_glp, name='get_only_grid_kardex_glp'),
    path('stock_product/', login_required(get_stock_product_store), name='stock_product'),

    # PDFKIT
    # path('kardex_glp_pdf/<int:pk>/', login_required(kardex_glp_pdf), name='kardex_glp_pdf'),
    # path('account_order_list_pdf/<int:pk>/',
    #      login_required(account_order_list_pdf), name='account_order_list_pdf'),

    # PANDA
    path('kardex_glp_excel/<int:pk>/', login_required(kardex_glp_excel), name='kardex_glp_excel'),

    # ESTADO DE CUENTA
    path('order_list/', login_required(order_list), name='order_list'),
    path('get_orders_by_client/', get_orders_by_client, name='get_orders_by_client'),
    path('get_order_detail_for_pay/', get_order_detail_for_pay, name='get_order_detail_for_pay'),
    path('new_loan_payment/', login_required(new_loan_payment), name='new_loan_payment'),
    path('get_order_detail_for_ball_change/', login_required(get_order_detail_for_ball_change),
         name='get_order_detail_for_ball_change'),
    path('new_ball_change/', login_required(new_ball_change), name='new_ball_change'),
    path('get_expenses/', login_required(get_expenses), name='get_expenses'),
    path('new_expense/', login_required(new_expense), name='new_expense'),

    # GENERADOR DE BOLETAS
    path('generate_receipt/', login_required(generate_receipt), name='generate_receipt'),
    path('generate_receipt_random/', login_required(generate_receipt_random), name='generate_receipt_random'),

    # PERCEPTRON
    path('PerceptronList/', login_required(PerceptronList), name='PerceptronList'),

    path('get_sales_all_subsidiaries/', login_required(get_sales_all_subsidiaries), name='get_sales_all_subsidiaries'),
    # recipe
    path('product_recipe_edit/', get_product_recipe_view, name='product_recipe_edit'),
    path('get_recipe_by_product/', get_recipe_by_product, name='get_recipe_by_product'),
    path('delete_recipe/', delete_recipe, name='delete_recipe'),
    path('save_update_recipe/', save_update_recipe, name='save_update_recipe'),

    # massive payment
    path('get_massiel_payment_form/', get_massiel_payment_form, name='get_massiel_payment_form'),
    path('new_massiel_payment/', new_massiel_payment, name='new_massiel_payment'),
    path('new_massiel_return/', new_massiel_return, name='new_massiel_return'),
    path('get_name_business/', get_name_business, name='get_name_business'),
    path('get_product_by_criteria/', get_product_by_criteria, name='get_product_by_criteria'),
    path('modal_family_save/', modal_family_save, name='modal_family_save'),
    path('save_family/', save_family, name='save_family'),
    path('save_category/', save_category, name='save_category'),
    path('save_subcategory/', save_subcategory, name='save_subcategory'),
    path('modal_category_save/', modal_category_save, name='modal_category_save'),
    path('modal_subcategory_save/', modal_subcategory_save, name='modal_subcategory_save'),
    path('modal_brand_save/', modal_brand_save, name='modal_brand_save'),
    path('save_brand/', save_brand, name='save_brand'),

    # print_ticket_internal
    path('print_ticket_order_sales/<int:pk>/<int:t>/', print_ticket_order_sales, name='print_ticket_order_sales'),
    path('print_quotation/<int:pk>/<str:t>/', print_quotation, name='print_quotation'),

    # report purchase
    path('get_costs_purchase/', login_required(get_costs_purchase_dates), name='get_costs_purchase'),
    # update address client
    path('update_address/', login_required(update_address), name='update_address'),
    path('get_order_by_correlative/', login_required(get_order_by_correlative), name='get_order_by_correlative'),
    path('get_product_sales_grid/', login_required(get_product_sales_grid), name='get_product_sales_grid'),
    path('info_product_detail/', login_required(info_product_detail), name='info_product_detail'),
    path('product_detail/', login_required(product_detail), name='product_detail'),

    path('get_product_sales_grid_new/', login_required(get_product_sales_grid_new), name='get_product_sales_grid_new'),

    path('get_modal_update_stock/', login_required(get_modal_update_stock), name='get_modal_update_stock'),
    path('new_update_stock/', login_required(new_update_stock), name='new_update_stock'),

    path('get_modal_change_price_purchase/', login_required(get_modal_change_price_purchase), name='get_modal_change_price_purchase'),
    path('new_change_price_purchase/', login_required(new_change_price_purchase), name='new_change_price_purchase'),

    path('print_order_bill/<int:pk>/<str:check>/', print_order_bill, name='print_order_bill'),

    # List quotation
    path('get_sales_quotation_by_subsidiary/', login_required(get_sales_quotation_by_subsidiary), name='get_sales_quotation_by_subsidiary'),

    # Cancel Order
    path('cancel_order/', login_required(cancel_order), name='cancel_order'),

    # New Client Sales
    path('save_new_client_sale/', login_required(save_new_client_sale), name='save_new_client_sale'),

    # New product modal
    path('get_modal_new_product/', login_required(get_modal_new_product), name='get_modal_new_product'),
    path('save_product_detail/', login_required(save_product_detail), name='save_product_detail'),

    # Update quotatio
    path('update_quotation/', login_required(update_quotation), name='update_quotation'),

    # Inventory_store
    path('inventory_store/', login_required(inventory_store), name='inventory_store'),
    path('save_register_inventory/', login_required(save_register_inventory), name='save_register_inventory'),
    path('save_register_inventory/', login_required(save_register_inventory), name='save_register_inventory'),
    path('save_new_inventory_product/', login_required(save_new_inventory_product), name='save_new_inventory_product'),
    path('get_products_by_inventory/', login_required(get_products_by_inventory), name='get_products_by_inventory'),
    path('close_inventory/', login_required(close_inventory), name='close_inventory'),
    path('get_last_inventory/', login_required(get_last_inventory), name='get_last_inventory'),
    
    # Clients_all
    path('get_clients_by_criteria/', login_required(get_clients_by_criteria), name='get_clients_by_criteria'),

    # Quotation
    path('quotation_list/', login_required(quotation_list), name='quotation_list'),
    path('get_product_quotation/', login_required(get_product_quotation), name='get_product_quotation'),
    path('save_quotation/', login_required(save_quotation), name='save_quotation'),
    path('delete_item_product/', login_required(delete_item_product), name='delete_item_product'),

    # Order Sales Print
    path('print_orders_sales/<str:start_date>/<str:end_date>/', print_orders_sales, name='print_orders_sales'),

    path('get_modal_change_price_purchase_dollar/', login_required(get_modal_change_price_purchase_dollar), name='get_modal_change_price_purchase_dollar'),
    path('new_change_price_purchase_dollar_product/', login_required(new_change_price_purchase_dollar_product), name='new_change_price_purchase_dollar_product'),

    # Delete presentation
    path('delete_product_detail/', login_required(delete_product_detail), name='delete_product_detail'),

    # Check Stock
    path('check_stock/', login_required(check_stock), name='check_stock'),

    # Refresh Stock
    path('refresh_stock/', login_required(refresh_stock), name='refresh_stock'),

    # Get Last Number
    path('get_last_id_type_others/', login_required(get_last_id_type_others), name='get_last_id_type_others'),

    # Report summary sales
    path('get_report_summary_sales/', login_required(get_report_summary_sales), name='get_report_summary_sales'),

    # All Products
    path('get_all_products/', login_required(get_all_products), name='get_all_products'),

    path('calculate_square_quantity/', login_required(calculate_square_quantity), name='calculate_square_quantity'),

    # EXCEL
    path('export_all_products/<str:start_date>/<str:end_date>/', login_required(export_all_products), name='export_all_products'),
    path('report_kardex_by_date/<str:date>/', login_required(report_kardex_by_date), name='report_kardex_by_date'),

    # SELL SERIAL
    path('modal_serial/', login_required(modal_serial), name='modal_serial'),

    # PRODUCT PHOTO
    path('get_product_photo/', login_required(get_product_photo), name='get_product_photo'),

    # SEARCH SELL
    path('search_sell_by_serial/', login_required(search_sell_by_serial), name='search_sell_by_serial'),

    # REPORT BRAND BY SALE
    path('report_sales_by_brand/', login_required(report_sales_by_brand), name='report_sales_by_brand'),

    # FUNCTION RECALCULATE
    path('recalculate/', login_required(recalculate), name='recalculate'),

    # SEARCH CLIENT
    path('get_client_search/', login_required(get_client_search), name='get_client_search'),

    path('get_correlative_by_type/', login_required(get_correlative_by_type), name='get_correlative_by_type'),

    path('save_order/', login_required(save_order), name='save_order'),

    path('modal_credit_note/', login_required(modal_credit_note), name='modal_credit_note'),
    path('save_credit_note/', login_required(save_credit_note), name='save_credit_note'),

    # Reporte de Notas de Crédito
    path('credit_notes_report/', login_required(get_credit_notes_report), name='credit_notes_report'),
    path('get_credit_notes_by_date/', login_required(get_credit_notes_by_date), name='get_credit_notes_by_date'),
    path('cancel_credit_note/', login_required(cancel_credit_note), name='cancel_credit_note'),

    # Product Serials
    path('get_product_serials/', login_required(get_product_serials), name='get_product_serials'),

]
