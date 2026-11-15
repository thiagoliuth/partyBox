from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("sobre/", views.sobre, name="sobre"),
    path("eventos/", views.evento_list, name="eventos"),
    path("meus-eventos/", views.meus_eventos, name="meus_eventos"),
    path("meus-eventos/<int:pk>/editar/", views.editar_evento, name="editar_evento"),
    path("meus-eventos/<int:pk>/excluir/", views.excluir_evento, name="excluir_evento"),
    path("cadastrar-evento/", views.cadastrar_evento, name="cadastrar_evento"),
]
