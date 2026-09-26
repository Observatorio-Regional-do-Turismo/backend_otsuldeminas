from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path("municipios/", MunicipiosView.as_view(), name = "Códigos dos municipios"),
    path("cnaes/", CNAEView.as_view(), name = "Informações dos cnaes"),
#    path("saldo/", SaldoMensalView.as_view()),
    path("estabelecimentos/", Estabelecimentos.as_view()),
    path("funcionarios/",Funcionarios.as_view()),
    path("postos_de_trabalho/",PostosDeTrabalho.as_view()),
    path("postos_de_trabalho_paginado/", PostosDeTrabalhoPaginado.as_view()),
    path("estoque_acumulado/", EstoqueAcumulado.as_view()),
    path("estoque_acumulado_paginado/", EstoqueAcumuladoPaginado.as_view()),
    
    # Rota para baixar o schema YAML/JSON
    #path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # Interface interativa do Swagger
    #path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Interface de leitura do Redoc (alternativa ao Swagger)
   #path('docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

