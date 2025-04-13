# core/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from core.models import Article, Category, NewsSource

def home(request):
    """Homepage view showing the list of articles with pagination."""
    # Get query parameters
    category_slug = request.GET.get('category')
    source_slug = request.GET.get('source')
    search_query = request.GET.get('q')
    
    # Start with all articles
    articles = Article.objects.select_related('source').prefetch_related('categories').all()
    
    # Apply filters if needed
    if category_slug:
        articles = articles.filter(categories__slug=category_slug)
    
    if source_slug:
        articles = articles.filter(source__slug=source_slug)
    
    if search_query:
        articles = articles.filter(title__icontains=search_query)
    
    # Get all categories and sources for the filter sidebar
    categories = Category.objects.all()
    sources = NewsSource.objects.filter(active=True)
    
    # Set up pagination
    paginator = Paginator(articles, 60)  # Show 60 articles per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'sources': sources,
        'selected_category': category_slug,
        'selected_source': source_slug,
        'search_query': search_query,
    }
    
    return render(request, 'core/home.html', context)

def article_detail(request, article_id):
    """View for displaying a single article."""
    article = get_object_or_404(Article.objects.select_related('source').prefetch_related('categories'), id=article_id)
    
    # Get related articles (same category)
    related_articles = Article.objects.filter(
        categories__in=article.categories.all()
    ).exclude(id=article.id).distinct().order_by('-published_at')[:5]
    
    # Process article content to ensure proper paragraph formatting
    content = article.content
    if content:
        # Ensure content has consistent newline formatting
        content = content.replace('\r\n', '\n')
        
        # If content doesn't have any newlines but has periods, add some basic formatting
        if '\n' not in content and '. ' in content:
            sentences = content.split('. ')
            if len(sentences) > 3:
                # Group sentences into paragraphs (approximately 3 sentences per paragraph)
                paragraphs = []
                current_paragraph = []
                
                for sentence in sentences:
                    current_paragraph.append(sentence)
                    if len(current_paragraph) >= 3:
                        paragraphs.append('. '.join(current_paragraph) + '.')
                        current_paragraph = []
                
                if current_paragraph:  # Add any remaining sentences
                    paragraphs.append('. '.join(current_paragraph) + '.')
                
                content = '\n\n'.join(paragraphs)
    
    # Update the article content with improved formatting
    article.content = content
    
    if content:
        content = content.replace('\r\n', '\n')  # sjednocení newlinů
        paragraphs = content.split('\n\n')  # rozdělení na odstavce
    else:
        paragraphs = []

    context = {
        'article': article,
        'related_articles': related_articles,
        'paragraphs': paragraphs,
    }
    
    return render(request, 'core/article_detail.html', context)