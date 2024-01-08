from django.contrib import admin
from .models import CustomCharge, Customer, ManualTransaction, Offer, Order, OrderItem, Product, ProductImage, CustomFieldValue, SellerInformation, StoreConfig, TaxConfig
from .models import CustomField, CategoryCustomField, Category
from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.html import escape
from django.utils.html import format_html
from mptt.admin import MPTTModelAdmin  # Import this if you are using django-mptt for Category

class OfferAdmin(admin.ModelAdmin):
    list_display = ('product', 'offer_type', 'value', 'start_date', 'end_date', 'is_active')
    list_filter = ('offer_type', 'start_date', 'end_date')
    search_fields = ('product__title', 'description')

    # Optionally, you can add more customizations here
    # For example, custom forms, fieldsets, actions, etc.

# Register the admin class with the associated model
admin.site.register(Offer, OfferAdmin)

# Category Admin
class CategoryAdmin(MPTTModelAdmin):  # Use MPTTModelAdmin for hierarchical models like Category
    list_display = ['title', 'status', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('title',)}


# SellerInformation Admin
class SellerInformationAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'phone_number', 'email', 'status', 'member_since']
    search_fields = ['contact_name', 'phone_number', 'email']



# Register your models here.
admin.site.register(Category, CategoryAdmin)

admin.site.register(SellerInformation, SellerInformationAdmin)

class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomField
        fields = '__all__'
        widgets = {
            'options': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(CustomFieldForm, self).__init__(*args, **kwargs)
        # Initialize your field choices here, or dynamically load them in the template with JavaScript
        if 'initial' in kwargs:
            field_type = kwargs['initial'].get('field_type', None)
        else:
            field_type = self.instance.field_type if self.instance else None

        if field_type:
            self.fields['options'].widget = self.get_widget_for_field_type(field_type)

    def get_widget_for_field_type(self, field_type):
        # Return the appropriate widget based on field_type
        if field_type == 'select':
            return forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter options separated by commas'})
        elif field_type == 'checkbox':
            return forms.CheckboxSelectMultiple()
        elif field_type == 'radio':
            return forms.RadioSelect()
      
        return forms.TextInput()  # Default widget

class CategoryCustomFieldForm(forms.ModelForm):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple("Categories", is_stacked=False)
    )

    class Meta:
        model = CategoryCustomField
        fields = '__all__'

class CategoryCustomFieldAdmin(admin.ModelAdmin):
    form = CategoryCustomFieldForm

    def save_model(self, request, obj, form, change):
        # Clear previous categories to prevent duplicates
        if change:
            obj.category.clear()
        
        # Save the custom field first
        super().save_model(request, obj, form, change)
        
        # Add the selected categories
        for category in form.cleaned_data['category']:
            CategoryCustomField.objects.create(custom_field=obj, category=category)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    form = CustomFieldForm
    list_display = ('name', 'field_type', 'get_categories')
    list_filter = ('field_type',)
    search_fields = ('name',)
    filter_horizontal = ('categories',)

    def get_categories(self, obj):
        return ", ".join([category.title for category in obj.categories.all()])
    get_categories.short_description = 'Categories'

@admin.register(CategoryCustomField)
class CategoryCustomFieldAdmin(admin.ModelAdmin):
    list_display = ('category', 'custom_field')
    list_filter = ('category',)
    search_fields = ('custom_field__name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class CustomFieldValueInline(admin.TabularInline):
    model = CustomFieldValue
    extra = 1

from django.utils.html import format_html

class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price',  'created_at', 'view_custom_fields', 'seller_or_company')

    def seller_or_company(self, obj):
        if hasattr(obj, 'seller_information') and obj.seller_information:
            # Assuming seller_information has a 'name' field or similar attribute
            return obj.seller_information.contact_name
        elif hasattr(obj, 'company_information') and obj.company_information:
            # Assuming company_information has a 'name' field or similar attribute
            return obj.company_information.name
        else:
            return "N/A"

    seller_or_company.short_description = "Seller/Company"

    
    search_fields = ('title', 'description')

    inlines = [ProductImageInline, CustomFieldValueInline]

    def owner_status(self, obj):
        return "Registered" if obj.seller_information.user else "Guest"

    def view_custom_fields(self, obj):
        custom_field_values = obj.custom_field_values.all()
        if custom_field_values:
            return format_html('<br>'.join([f'{cfv.custom_field.name}: {cfv.value}' for cfv in custom_field_values]))
        return "No Custom Fields"

    view_custom_fields.short_description = 'Custom Fields'

admin.site.register(Product, ProductAdmin)


from .models import StoreProduct, StoreProductStockEntry

class StoreProductStockEntryInline(admin.TabularInline):
    model = StoreProductStockEntry
    extra = 1  # Number of extra forms to display
    fields = ['quantity_added', 'purchase_price', 'date_added']
    readonly_fields = ['date_added']  # Set date_added as read-only

class StoreProductAdmin(admin.ModelAdmin):
    list_display = ('store', 'product_title', 'sale_price', 'stock_quantity', 'is_store_exclusive', 'created_at', 'updated_at')
    list_filter = ('store', 'is_store_exclusive')
    search_fields = ('store__name', 'custom_title', 'product__title')
    inlines = [StoreProductStockEntryInline]  # Add the inline here


    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Assuming you have fields to input stock addition in your admin
        added_stock = form.cleaned_data.get('added_stock', 0)
        purchase_price = form.cleaned_data.get('purchase_price', None)
        if added_stock:
            obj.add_stock(added_stock, purchase_price)

    def product_title(self, obj):
        return obj.custom_title if obj.custom_title else (obj.product.title if obj.product else "Exclusive Product")
    product_title.short_description = "Product Title"

admin.site.register(StoreProduct, StoreProductAdmin)

# OrderItem Inline Admin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # Number of extra forms to display
    fields = ['product', 'quantity', 'price']
    readonly_fields = ['total_price']

# Order Admin
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'customer', 'total_price', 'created_at', 'updated_at')
    list_filter = ('store', 'created_at')
    search_fields = ('store__name', 'customer__name')
    inlines = [OrderItemInline]  # Add the inline here

    def total_price(self, obj):
        return sum(item.total_price for item in obj.items.all())
    total_price.short_description = "Total Price"

admin.site.register(Order, OrderAdmin)

# OrderItem Admin (Optional)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order', 'product')
    search_fields = ('order__id', 'product__product__title')

admin.site.register(OrderItem, OrderItemAdmin)

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('mobile', 'name', 'email', 'store', 'created_at', 'updated_at')  # Fields to display in admin list view
    search_fields = ('mobile', 'name', 'email')  # Fields to be searchable in admin
    list_filter = ('store', 'created_at')  # Fields to filter by in admin
    ordering = ('-created_at',)  # Default ordering

# Register your models here.
admin.site.register(Customer, CustomerAdmin)


@admin.register(StoreConfig)
class StoreConfigAdmin(admin.ModelAdmin):
    list_display = ['store', 'default_discount_type', 'default_discount_value']
    search_fields = ['store__name']

@admin.register(TaxConfig)
class TaxConfigAdmin(admin.ModelAdmin):
    list_display = ['store', 'name', 'rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'store__name']

@admin.register(CustomCharge)
class CustomChargeAdmin(admin.ModelAdmin):
    list_display = ['store', 'name', 'charge_type', 'value']
    search_fields = ['name', 'store__name']


class ManualTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'transaction_type', 'transaction_date', 'notes')
    list_filter = ('transaction_type', 'transaction_date')
    search_fields = ('customer__name', 'customer__mobile')

    def get_readonly_fields(self, request, obj=None):
        # Make all fields read-only if editing an existing object
        if obj:
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

admin.site.register(ManualTransaction, ManualTransactionAdmin)
