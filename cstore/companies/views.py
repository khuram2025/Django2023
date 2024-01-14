from decimal import Decimal
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from product.models import Category, Customer, ManualTransaction, Order, OrderItem, Product, StoreProduct, TaxConfig
from django.views.decorators.csrf import csrf_exempt
from locations.models import Address, City, Country
from .forms import CompanyProfileForm
from .models import CompanyProfile, Schedule
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .forms import CompanyProfileForm
import json
from collections import defaultdict

from companies.models import CompanyProfile
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from account.models import CustomUser, UserProfile  # Import your CustomUser model
from django.dispatch import receiver
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Sum
import base64
from django.contrib.auth.decorators import login_required
from account.forms import UserProfileForm
import os


@login_required
def create_company(request):
    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES)
        # Shorten the filenames if they are too long
        for field in ['logo', 'cover_pic']:
            if field in request.FILES:
                file = request.FILES[field]
                if len(file.name) > 100:
                    # Keep the extension, shorten the filename
                    name, ext = os.path.splitext(file.name)
                    file.name = name[:100 - len(ext)] + ext
        print("POST Data:", request.POST)
        print("FILES Data:", request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user 
            company.save()
            return redirect('companies:company-public', pk=company.pk)
        else:
            print("Form Errors:", form.errors)  # Print form errors
    else:
        form = CompanyProfileForm()
    print("City field choices:", form.fields['city'].queryset)
    return render(request, 'companies/create_company.html', {'form': form})



@login_required
def create_or_edit_company(request, pk=None):
    # If pk is provided, we're editing an existing company
    if pk:
        company = get_object_or_404(CompanyProfile, pk=pk, owner=request.user)
        form = CompanyProfileForm(request.POST or None, request.FILES or None, instance=company)
    else:
        # Otherwise, we're creating a new company
        form = CompanyProfileForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        # Shorten the filenames if they are too long
        for field in ['logo', 'cover_pic']:
            if field in request.FILES:
                file = request.FILES[field]
                if len(file.name) > 100:
                    name, ext = os.path.splitext(file.name)
                    file.name = name[:100 - len(ext)] + ext

        print("POST Data:", request.POST)
        print("FILES Data:", request.FILES)

        if form.is_valid():
            company = form.save(commit=False)
            if not pk:  # Set the owner only if creating a new company
                company.owner = request.user
            company.save()
            return redirect('companies:company-public', pk=company.pk)
        else:
            print("Form Errors:", form.errors)

    context = {
        'form': form,
        'is_editing': pk is not None,  # Pass this to the template to change the UI based on create/edit
        'company': company if pk else None ,
    }
    return render(request, 'companies/create_or_edit_company.html', context)



@login_required
def company_edit(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    companies = user.owned_companies.all()
    categories = Category.objects.all()

    main_company = companies.first() if companies.exists() else None
    selected_category_ids = []
    if main_company:
        selected_category_ids = main_company.working_categories.values_list('id', flat=True)


    main_branch = main_company.branches.first() if main_company and main_company.branches.exists() else None

    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=main_company)
        if form.is_valid():
            company = form.save(commit=False)

            company.facebook_link = form.cleaned_data.get('facebook_link', '')
            company.twitter_link = form.cleaned_data.get('twitter_link', '')
            company.youtube_link = form.cleaned_data.get('youtube_link', '')
            company.instagram_link = form.cleaned_data.get('instagram_link', '')


            # Handle address data
            address_data = {'line1': form.cleaned_data.get('line1')}
            city = form.cleaned_data.get('city')
            if city:
                address_data['city'] = city
            address, addr_created = Address.objects.get_or_create(**address_data)
            company.address = address
            company.save()

            # Handle working categories
            working_categories = form.cleaned_data.get('working_categories')
            company.working_categories.set(working_categories)

            return redirect('companies:company-public')  # Adjust the redirect as needed
        else:
            print("Form errors:", form.errors)
    else:
        form = CompanyProfileForm(instance=main_company)

    day_choices = Schedule.DAY_CHOICES

    context = {
        'form': form,
        'profile': profile,
        'companies': companies,
        'branch': main_branch,
        'day_choices': day_choices,
        'main_company': main_company,
        'selected_category_ids': selected_category_ids,
        'categories': categories,
    }

    return render(request, 'companies/company_detail.html', context)

def company_profile_detail(request, pk):
    # Get the company profile or 404 if not found
    company = get_object_or_404(CompanyProfile, pk=pk)

    # Fetch branches and their related data
    branches_with_details = []
    for branch in company.branches.all():
        schedules = branch.schedules.all()
        phone_numbers = branch.phone_numbers_rel.all()
        address = branch.address

        branches_with_details.append({
            'branch': branch,
            'schedules': schedules,
            'phone_numbers': phone_numbers,
            'address': address
        })
        
      # Get city and category filter values from request
    city_id = request.GET.get('city')
    category_id = request.GET.get('category')

    # Apply filters to company products
    product_filters = {'company': company}
    if city_id:
        product_filters['city_id'] = city_id
    if category_id:
        product_filters['category_id'] = category_id
    company_products = Product.objects.filter(**product_filters)

    # Fetch all cities and categories for filter dropdowns
    cities = City.objects.all()
    categories = Category.objects.all()

    # Prepare context
    context = {
        'company': company,
        'branches_with_details': branches_with_details,
        'company_products': company_products,
        'cities': cities,
        'categories': categories,
    }
    

    return render(request, 'companies/company_public.html', context)


def list_companies(request):
    city_id = request.GET.get('bpCity')  # Get the city ID from the request
    category_id = request.GET.get('bpCategory')  # Get the category ID from the request

    # Print the received city and category IDs for debugging
    print("Received City ID: ", city_id)
    print("Received Category ID: ", category_id)

    # Filter by both city and category if provided
    filters = {}
    if city_id:
        filters['address__city_id'] = city_id
    if category_id:
        filters['working_categories__id'] = category_id

    companies = CompanyProfile.objects.filter(**filters)

    cities = City.objects.all()
    categories = Category.objects.all()

    context = {
        'companies': companies,
        'cities': cities,
        'categories': categories,
    }

    return render(request, 'companies/companies_list.html', context)



def company_dashboard(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    return render(request, 'companies/company_dashboard.html', {'company': company})

def company_inventory(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    store_products = StoreProduct.objects.filter(store=company)

    total_stock_value = 0
    total_profit = 0
    total_purchase_value = 0

    for product in store_products:
        current_stock_value = product.current_stock * (product.purchase_price or 0)
        total_stock_value += current_stock_value

        profit_per_unit = (product.sale_price or 0) - (product.purchase_price or 0)
        total_profit += profit_per_unit * product.current_stock

        total_purchase_value += (product.purchase_price or 0) * product.current_stock

    # Calculating average profit percentage
    average_profit_percentage = 0
    if total_purchase_value > 0:
        average_profit_percentage = (total_profit / total_purchase_value) * 100

    total_stock = sum(product.stock_quantity for product in store_products)
    total_unique_products = store_products.count()

    context = {
        'company': company,
        'store_products': store_products,
        'total_stock': total_stock,
        'total_unique_products': total_unique_products,
        'total_stock_value': total_stock_value,
        'total_profit': total_profit,
        'average_profit_percentage': average_profit_percentage,
        'pk': pk
    }

    return render(request, 'companies/items_list.html', context)



def company_inventory_api(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    store_products = StoreProduct.objects.filter(store=company)

    total_stock_value = 0
    total_profit = 0
    total_purchase_value = 0

    for product in store_products:
        current_stock_value = product.current_stock * (product.purchase_price or 0)
        total_stock_value += current_stock_value

        profit_per_unit = (product.sale_price or 0) - (product.purchase_price or 0)
        total_profit += profit_per_unit * product.current_stock

        total_purchase_value += (product.purchase_price or 0) * product.current_stock

    average_profit_percentage = 0
    if total_purchase_value > 0:
        average_profit_percentage = (total_profit / total_purchase_value) * 100

    total_stock = sum(product.stock_quantity for product in store_products)
    total_unique_products = store_products.count()

    # Serialize the data
    store_products_data = []
    for product in store_products:
        # Assuming product.product.images.all() returns a queryset of Image objects
        image_url = product.product.images.all()[0].image.url if product.product.images.exists() else None

        store_products_data.append({
            'id': product.id,
            'name': product.custom_title if product.custom_title else (product.product.title if product.product else "Exclusive Product"),
            'current_stock': product.current_stock,
            'purchase_price': product.purchase_price,
            'sale_price': product.sale_price,
            'image_url': image_url,  # Add the image URL
            # Add more fields as needed
        })


    context = {
        'company_id': company.id,
        'company_name': company.name,  # or however you want to represent the company
        'store_products': store_products_data,
        'total_stock': total_stock,
        'total_unique_products': total_unique_products,
        'total_stock_value': total_stock_value,
        'total_profit': total_profit,
        'average_profit_percentage': average_profit_percentage,
    }

    print("Sending API response data:", context)

    return JsonResponse(context)

def store_product_detail_api(request, store_product_id):
    # Fetch the store product by ID
    store_product = get_object_or_404(StoreProduct, pk=store_product_id)

    # Serialize the store product data
    store_product_data = {
        'id': store_product.id,
        'store_id': store_product.store.id,
        'custom_title': store_product.custom_title or (store_product.product.title if store_product.product else ''),
        'custom_description': store_product.custom_description or (store_product.product.description if store_product.product else ''),
        'sale_price': store_product.sale_price,
        'stock_quantity': store_product.stock_quantity,
        'is_store_exclusive': store_product.is_store_exclusive,
        'purchase_price': store_product.purchase_price,
        'opening_stock': store_product.opening_stock,
        'low_stock_threshold': store_product.low_stock_threshold,
        'current_stock': store_product.current_stock,
    }

    # Include product details if it's linked
    if store_product.product:
        store_product_data['product'] = {
            'id': store_product.product.id,
            'title': store_product.product.title,
            'description': store_product.product.description,
        }

    # Fetch and serialize sales data
    sales_data = []
    order_items = OrderItem.objects.filter(product=store_product)
    for item in order_items:
        order = item.order
        customer = order.customer
        sales_data.append({
            'order_id': order.id,
            'customer_name': customer.name if customer else 'N/A',
            'customer_mobile': customer.mobile if customer else 'N/A',
            'quantity_sold': item.quantity,
            'selling_price': item.price,
            'total_price': item.total_price
        })

    store_product_data['sales'] = sales_data

    print("Product Detail response data:", store_product_data)

    return JsonResponse(store_product_data)

def pos_api(request, store_id):
    store = get_object_or_404(CompanyProfile, pk=store_id)
    store_products = StoreProduct.objects.filter(store=store).select_related('product__category')

    products_data = []
    categories_set = set()  # Use a set to store unique category ids
    categories_data = []  # List to store category data

    for product in store_products:
        category = product.product.category if product.product and product.product.category else None
        if category and category.id not in categories_set:
            categories_set.add(category.id)
            categories_data.append({
                'id': category.id,
                'title': category.title,
                'description': category.description,
                'status': category.status,
                'icon': category.icon.url if category.icon else None,
                'image': category.image.url if category.image else None,
                # Additional category fields as needed
            })

        image_url = product.product.images.first().image.url if product.product and product.product.images.exists() else None

        products_data.append({
            'id': product.id,
            'name': product.custom_title or (product.product.title if product.product else ''),
            'stock_quantity': product.current_stock,
            'category': category.title if category else "Uncategorized",
            'sale_price': product.sale_price,
            'purchase_price': product.purchase_price,
            'image_url': image_url,
            # Additional product fields as needed
        })

        # Fetch tax configurations for the store
        tax_configs = TaxConfig.objects.filter(store=store, is_active=True)
        tax_data = [{
                'id': tax.id,
                'name': tax.name,
                'rate': tax.rate,
                'is_active': tax.is_active
        } for tax in tax_configs]

        customers = Customer.objects.filter(store=store)
        customers_data = [{'id': cust.id, 'name': cust.name, 'email': cust.email, 'mobile': cust.mobile} for cust in customers]

        context = {
            'store_id': store.id,
            'store_name': store.name,
            'products': products_data,
            'categories': categories_data,  # Include categories in the context
            'customers': customers_data,
            'taxes': tax_data,
        }

        print("POS API response data:", context)
    return JsonResponse(context)

@csrf_exempt
def order_summary(request, store_id):
    if request.method == 'POST':
        try:
            # Decode JSON from request body
            order_data = json.loads(request.body.decode('utf-8'))

            # Print the received order data for debugging
            print("Received order data:", order_data)

            # Extract and handle data
            customer_id = order_data.get('customer_id', None)
            customer = Customer.objects.get(id=customer_id) if customer_id else None

            # Process the order
            order = process_order(store_id, order_data, customer)

            # Fetch customers for the store
            customers = Customer.objects.filter(store_id=store_id)
            customers_list = [{'id': cust.id, 'name': cust.name, 'email': cust.email} for cust in customers]

            return JsonResponse({'order_id': order.id, 'summary': format_order_summary(order), 'customers': customers_list})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

def process_order(store_id, order_data, customer):
    store = get_object_or_404(CompanyProfile, pk=store_id)

    # Extracting payment details
    payment_type = order_data.get('payment_type', 'cash').lower()

    paid_amount = Decimal(order_data.get('paid_amount', 0))
    credit_amount = Decimal(order_data.get('credit_amount', 0))

    subtotal = Decimal(order_data['subtotal'])
    discount_value = Decimal(order_data['discount_value'])
    discount_type = 'percentage' if order_data['is_discount_percentage'] else 'amount'
    total_price = Decimal(order_data['total_price'])
    tax_ids = order_data.get('tax_ids', [])

    print("Payment type before creating order:", payment_type)


    # Create order with payment details
    order = Order.objects.create(
        store=store,
        customer=customer,
        subtotal=subtotal,
        discount_type=discount_type,
        discount_value=discount_value,
        total_price=total_price,
        payment_type=payment_type,
        paid_amount=paid_amount,
        credit_amount=credit_amount
    )
    print("Created order details:", order.payment_type, order.paid_amount, order.credit_amount)

    # Add overall taxes to the order
    for tax_id in tax_ids:
        tax = get_object_or_404(TaxConfig, pk=tax_id)
        order.taxes.add(tax)

    # Process each order item
    for item_data in order_data['items']:
        store_product = get_object_or_404(StoreProduct, pk=item_data['product_id'])
        quantity = item_data['quantity']
        item_tax_ids = item_data.get('item_tax_ids', [])  # Item-level taxes

        if store_product.current_stock < quantity:
            raise ValueError(f"Not enough stock for product {store_product.product.title}")

        store_product.current_stock -= quantity
        store_product.save()

        order_item = OrderItem.objects.create(
            order=order,
            product=store_product,
            quantity=quantity,
            price=store_product.sale_price
        )

        # Add item-level taxes
        for tax_id in item_tax_ids:
            tax = get_object_or_404(TaxConfig, pk=tax_id)
            order_item.taxes.add(tax)

    # Print the tax information for debugging
    for tax in order.taxes.all():
        print(f"Tax: {tax.name}, Rate: {tax.rate}")

    return order


def format_order_summary(order):
    # Format the order summary data
    summary = {
        'order_id': order.id,
        # Add other necessary order details
    }
    return summary

def store_product_detail(request, pk, product_pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    store_product = get_object_or_404(StoreProduct, pk=product_pk, store=company)
    stock_entries = store_product.stock_entries.order_by('-date_added')

    # Fetch other vendors who have the same product
    similar_store_products = StoreProduct.objects.filter(
        product=store_product.product
    ).exclude(
        store=company
    )
    order_items = OrderItem.objects.filter(product=store_product)
    customer_aggregate = defaultdict(lambda: {'quantity': 0, 'total_price': 0})
    for item in order_items:
        customer = item.order.customer
        if customer:
            key = (customer.name, customer.mobile)
            customer_aggregate[key]['quantity'] += item.quantity
            customer_aggregate[key]['total_price'] += item.total_price  # Corrected line
        else:
            key = ('Walk In Customer', '')
            customer_aggregate[key]['quantity'] += item.quantity
            customer_aggregate[key]['total_price'] += item.total_price  # Corrected line


    customer_purchases = [
        {
            'name': key[0],
            'mobile': key[1],
            'total_quantity': value['quantity'],
            'total_price': value['total_price']
        }
        for key, value in customer_aggregate.items()
    ]



    context = {
        'company': company,
        'store_product': store_product,
        'stock_entries': stock_entries,
        'similar_store_products': similar_store_products,
        'store_id': company.id,  # Adding store_id to context
        'customer_purchases': customer_purchases,
        'product_id': store_product.id,
        'pk': pk
    }

    return render(request, 'companies/product_detail.html', context)



def list_customers_api(request, company_id):
    # Fetch the company profile by ID
    company_profile = get_object_or_404(CompanyProfile, pk=company_id)

    # Fetch customers belonging to the company
    customers = Customer.objects.filter(store=company_profile)

    # Serialize customer data along with their orders
    customers_data = []
    for customer in customers:
        # Serialize each customer's orders
        customer_orders = []
        for order in customer.customer_orders.all():
            # Serialize each order item
            order_items = []
            for item in order.items.all():
                order_items.append({
                    'id': item.id,
                    'product_title': item.product.product.title,  # Adjust field based on your model
                    'quantity': item.quantity,
                    'price': item.price,
                    'total_price': item.total_price
                })

            customer_orders.append({
                'id': order.id,
                'total_price': order.total_price,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat(),
                'items': order_items
            })

        customers_data.append({
            'id': customer.id,
            'mobile': customer.mobile,
            'name': customer.name,
            'email': customer.email,
            'openingBalance': customer.opening_balance,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat(),
            'orders': customer_orders  # Add orders to customer data
        })

    # Context to be returned
    context = {
        'company_id': company_profile.id,
        'company_name': company_profile.name,  # Assuming CompanyProfile has a name field
        'customers': customers_data,
    }

    print("Sending API response data:", context)

    return JsonResponse(context)

def customer_detail_api(request, company_id, customer_id):
    # Fetch the customer by ID within the specified company
    customer = get_object_or_404(Customer, pk=customer_id, store_id=company_id)

    # Serialize customer's orders
    orders_data = []
    for order in customer.customer_orders.all():
        orders_data.append({
            'id': order.id,
            'total_price': order.total_price,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            # Include other order fields as necessary
        })

    # Serialize customer data
    customer_data = {
        'id': customer.id,
        'mobile': customer.mobile,
        'name': customer.name,
        'email': customer.email,
        'created_at': customer.created_at.isoformat(),
        'updated_at': customer.updated_at.isoformat(),
        'orders': orders_data  # Add orders to customer data
    }

    return JsonResponse(customer_data)

@csrf_exempt
@require_http_methods(["POST"])
def create_customer_api(request):
    try:
        # Log the raw request body for debugging
        print(f"Raw request body: {request.body}")

        # Parse the JSON body of the request
        data = json.loads(request.body)
        print(f"Parsed JSON data: {data}")

        # Validate and create a new customer
        customer = Customer(
            mobile=data.get('mobile'),
            name=data.get('name', ''),
            email=data.get('email', ''),
            store_id=data.get('store_id'),  # Assuming this is passed in the request
            opening_balance=data.get('opening_balance', 0.00)  # Set default to 0.00 if not provided
        )
        customer.full_clean()  # This will raise a ValidationError if the data is not valid
        customer.save()

        # Return the created customer data
        return JsonResponse({
            'id': customer.id,
            'mobile': customer.mobile,
            'name': customer.name,
            'email': customer.email,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat(),
            'opening_balance': customer.opening_balance  # Include opening_balance in the response
        })

    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return HttpResponseBadRequest("Invalid JSON")
    except ValidationError as e:
        print(f"Validation error: {e.messages}")
        return HttpResponseBadRequest(f"Invalid data: {e.messages}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return HttpResponseBadRequest(f"Error: {e}")

def list_taxes_api(request, company_id):
    # Fetch the company profile by ID
    company_profile = get_object_or_404(CompanyProfile, pk=company_id)

    # Fetch tax configurations belonging to the company
    taxes = TaxConfig.objects.filter(store=company_profile)

    # Serialize tax configuration data
    taxes_data = []
    for tax in taxes:
        taxes_data.append({
            'id': tax.id,
            'name': tax.name,
            'rate': tax.rate,
            'is_active': tax.is_active
        })

    # Context to be returned
    context = {
        'company_id': company_profile.id,
        'company_name': company_profile.name,  # Assuming CompanyProfile has a name field
        'taxes': taxes_data,
    }

    print("Sending API response data:", context)

    return JsonResponse(context)


def fetch_customer_orders(request, customerId):
    orders = Order.objects.filter(customer_id=customerId).select_related('customer')

    orders_data = [{
        'id': order.id,
        'imageUrl': getattr(order, 'image_url', None),
        'customerName': order.customer.name if order.customer else None,
        'mobileNumber': order.customer.mobile if order.customer else None,
        'date': order.created_at.strftime('%Y-%m-%d') if order.created_at else None,
        'transactionType': getattr(order, 'payment_type', None),
        'totalAmount': order.total_price if order.total_price else None,
        'paidAmount': float(order.paid_amount) if order.paid_amount else 0.0,  # Convert to float for JSON serialization
        'creditAmount': float(order.credit_amount) if order.credit_amount else 0.0,  # Convert to float for JSON serialization
    } for order in orders]

    print("Sending Customer Orders:", orders_data)
    return JsonResponse({'orders': orders_data})

def customer_ledger(request, customerId):
    orders = Order.objects.filter(customer_id=customerId).select_related('customer')
    manual_transactions = ManualTransaction.objects.filter(customer_id=customerId)

    total_sales = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_payments = orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0

    ledger_entries = []

    for order in orders:
        # Add sale entry
        ledger_entries.append({
            'id': order.id,
            'type': 'sale',
            'date': order.created_at.strftime('%Y-%m-%d'),
            'amount': order.total_price,
        })

        # Add payment entry if there is a payment
        if order.paid_amount > 0:
            ledger_entries.append({
                'id': order.id,
                'type': 'payment',
                'date': getattr(order, 'payment_date', order.created_at).strftime('%Y-%m-%d'),
                'amount': order.paid_amount,
                # ... other relevant fields ...
            })

    for transaction in manual_transactions:
        ledger_entries.append({
            'id': transaction.id,
            'type': transaction.transaction_type,  # 'in' or 'out'
            'date': transaction.transaction_date.strftime('%Y-%m-%d'),
            'amount': transaction.amount,
            'is_manual': True  # Indicator for manual transactions
    })
            

    # Sort entries by date
    ledger_entries.sort(key=lambda x: x['date'])
    print("Sending Customer Orders:", ledger_entries)
    return JsonResponse({'ledger_entries': ledger_entries})

@csrf_exempt  # This is for demonstration purposes. It's not recommended for production without proper CSRF protection.
@require_http_methods(["POST"])
def add_manual_transaction(request):
    try:
        # Parse request body
        data = json.loads(request.body)
       
        # Validate the required fields
        required_fields = ['customer_id', 'amount', 'transaction_type']
        if not all(field in data for field in required_fields):
            return HttpResponseBadRequest('Missing required fields.')

        # Validate the customer
        try:
            customer = Customer.objects.get(pk=data['customer_id'])
        except Customer.DoesNotExist:
            return HttpResponseBadRequest('Customer does not exist.')

        # Validate the transaction type
        if data['transaction_type'] not in dict(ManualTransaction.TRANSACTION_CHOICES):
            return HttpResponseBadRequest('Invalid transaction type.')

        # Create the manual transaction
        transaction = ManualTransaction.objects.create(
            customer=customer,
            amount=Decimal(data['amount']),
            transaction_type=data['transaction_type'],
            transaction_date=data.get('transaction_date'),
            notes=data.get('notes', '')
        )

        print("Transaction created successfully:", transaction.id)  # Log transaction creation

        # Return success response
        return JsonResponse({
            'id': transaction.id,
            'customer': transaction.customer.id,
            'amount': transaction.amount,
            'transaction_type': transaction.transaction_type,
            'transaction_date': transaction.transaction_date,
            'notes': transaction.notes
        })

    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)  # Log JSON parsing error
        return HttpResponseBadRequest('Invalid JSON.')
    except Exception as e:
        print("Exception occurred:", e)  # Log general exception
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def add_inventory(request):
    return render(request, 'product/add_company_product.html')
