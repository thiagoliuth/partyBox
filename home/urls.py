from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("sobre/", views.sobre, name="sobre"),
    path("eventos/", views.evento_list, name="eventos"),
    path("meus-eventos/", views.meus_eventos, name="meus_eventos"),
    path("cadastrar-evento/", views.cadastrar_evento, name="cadastrar_evento"),
]
