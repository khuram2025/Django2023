from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    # ... other url patterns
    path('add_product/', views.create_product, name='add_product'),
    path('add_product_company/', views.create_company_product, name='add_product_company'),
    path('search-cities/', views.search_cities, name='search_cities'),
    path('ajax/load-subcategories/', views.load_subcategories, name='ajax_load_subcategories'),  # URL for loading subcategories via AJAX

    path('company/<int:pk>/product/create', views.create_or_import_product, name='create_or_import_product'),

    path('products/', views.product_list, name='product_list'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('search/', views.product_search, name='product_search'),

    path('user/<int:user_pk>/products/', views.user_product_list, name='user_product_list'),
    path('ajax/load-custom-fields/', views.ajax_load_custom_fields, name='ajax_load_custom_fields'),
    path('ajax/get-product-details/', views.get_product_details, name='get_product_details'),
    
]
