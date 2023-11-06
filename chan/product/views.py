from django.shortcuts import render, redirect, get_object_or_404
from .models import Product
from .forms import ProductForm
from django.http import JsonResponse
from .models import Category, City, ProductImage
from django.contrib import messages

def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        print("Received POST data:", request.POST)  # Print submitted POST data
        print("Received FILES data:", request.FILES)  # Print submitted FILES data
        
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.save()  # Save the product to get an ID for the foreign key
                
                # Handle the images
                images = request.FILES.getlist('images')
                for image in images:
                    ProductImage.objects.create(product=product, image=image)
                
                messages.success(request, 'Product added successfully!')
                return redirect('product_detail', pk=product.pk)  # Assuming you have a view named 'product_detail'
            except Exception as e:
                print("Error during save process:", e)  # Print exception message
                messages.error(request, f"Error occurred during save process: {e}")
                # Optionally, log the error here
        else:
            print("Form errors:", form.errors)  # Print form errors
            messages.error(request, "There was an error with the form. Please check the details.")
    else:
        form = ProductForm()

    return render(request, 'product/add_product.html', {
        'form': form
    })



from django.http import JsonResponse

def load_subcategories(request):
    main_category_id = request.GET.get('category_id')
    subcategories = Category.objects.filter(parent_id=main_category_id).order_by('title')  # Changed 'name' to 'title'
    return JsonResponse(list(subcategories.values('id', 'title')), safe=False)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product/product_detail.html', {'product': product})


def product_list(request):
    products = Product.objects.all()  # Get all products
    return render(request, 'product/product_listing.html', {'products': products})



def search_cities(request):
    if 'searchTerm' in request.GET:
        query = request.GET.get('searchTerm')
        cities = City.objects.filter(name__icontains=query).values('id', 'name')
        return JsonResponse(list(cities), safe=False)
    return JsonResponse([], safe=False)


