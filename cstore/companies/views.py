from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from product.models import Category, Product

from locations.models import Address, City, Country
from .forms import CompanyProfileForm
from .models import CompanyProfile, Schedule
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.urls import reverse
from django.contrib import messages
from .forms import CompanyProfileForm

from companies.models import CompanyProfile

from django.contrib.auth.models import User
from account.models import CustomUser, UserProfile  # Import your CustomUser model
from django.dispatch import receiver
from django.conf import settings
from django.core.files.base import ContentFile
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
    return render(request, 'companies/items_list.html', {'company': company})

@login_required
def add_inventory(request):
    return render(request, 'product/add_company_product.html')
