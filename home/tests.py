from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import EventoForm
from .models import Evento


class CadastroEventoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="organizador", email="organizador@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="outro", email="outro@example.com", password="senha-teste"
        )

    def setUp(self):
        self.url = reverse("cadastrar_evento")
        self.dados = {
            "nome": "Festival",
            "descricao": "Festival de música",
            "dataEvento": "2030-12-01",
            "horarioEvento": "18:00",
            "siglaEstado": "SP",
            "cidade": "São Paulo",
            "bairro": "Centro",
            "rua": "Rua do Festival",
            "numero": "10",
            "ehPublico": "on",
        }

    def test_anonimo_get_e_post_exigem_login(self):
        for metodo in ("get", "post"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.url, self.dados if metodo == "post" else {})

                self.assertRedirects(
                    response,
                    f"{reverse('admin:login')}?next={self.url}",
                    fetch_redirect_response=False,
                )
                self.assertFalse(Evento.objects.exists())

    def test_autenticado_cria_evento_sem_enviar_usuario(self):
        self.client.force_login(self.usuario)

        response = self.client.post(self.url, self.dados)

        self.assertRedirects(response, reverse("index"))
        self.assertEqual(Evento.objects.count(), 1)
        self.assertEqual(Evento.objects.get().usuario, self.usuario)

    def test_usuario_forjado_nao_altera_dono_do_evento(self):
        self.client.force_login(self.usuario)
        self.dados["usuario"] = self.outro_usuario.pk

        response = self.client.post(self.url, self.dados)

        self.assertRedirects(response, reverse("index"))
        self.assertEqual(Evento.objects.count(), 1)
        self.assertEqual(Evento.objects.get().usuario, self.usuario)

    def test_formulario_nao_expoe_usuario(self):
        form = EventoForm()

        self.assertNotIn("usuario", form.fields)
        self.assertNotIn("usuario", form.Meta.widgets)
        self.assertNotIn('name="usuario"', form.as_p())


class MeusEventosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="dono", email="dono@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="visitante", email="visitante@example.com", password="senha-teste"
        )
        dados = {
            "descricao": "Descrição",
            "siglaEstado": "SP",
            "cidade": "São Paulo",
            "bairro": "Centro",
            "rua": "Rua",
            "numero": "1",
        }
        cls.eventos = [
            Evento.objects.create(
                usuario=cls.usuario, nome=nome, dataEvento=data,
                horarioEvento=horario, **dados
            )
            for nome, data, horario in [
                ("Zulu", "2030-12-02", "09:00"),
                ("Alfa", "2030-12-01", "18:00"),
                ("Alfa", "2030-12-01", "09:00"),
                ("Beta", "2030-12-01", "09:00"),
            ]
        ]

    def setUp(self):
        self.url = reverse("meus_eventos")

    def test_anonimo_get_e_post_exigem_login(self):
        for metodo in ("get", "post"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.url)
                self.assertRedirects(
                    response, f"{reverse('admin:login')}?next={self.url}",
                    fetch_redirect_response=False,
                )

    def test_lista_apenas_eventos_do_usuario_com_categoria_precarregada(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"usuario": self.outro_usuario.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/meus_eventos.html")
        self.assertEqual(set(response.context["eventos"]), set(self.eventos))
        self.assertEqual(response.context["eventos"].query.select_related, {"categoria": {}})

        self.client.force_login(self.outro_usuario)
        response = self.client.get(self.url, {"usuario": self.usuario.pk})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["eventos"], [])

    def test_ordem_nome_padrao_e_desempate_por_pk(self):
        self.client.force_login(self.usuario)
        for parametros in ({}, {"ordem": "nome"}):
            with self.subTest(parametros=parametros):
                response = self.client.get(self.url, parametros)
                self.assertEqual(response.context["ordem"], "nome")
                self.assertEqual(
                    list(response.context["eventos"]),
                    [self.eventos[i] for i in (1, 2, 3, 0)],
                )

    def test_ordem_data_horario_e_desempate_por_pk(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"ordem": "data"})
        self.assertEqual(response.context["ordem"], "data")
        self.assertEqual(
            list(response.context["eventos"]),
            [self.eventos[i] for i in (2, 3, 1, 0)],
        )

    def test_ordem_invalida_retorna_nome(self):
        self.client.force_login(self.usuario)
        for ordem in ("", "-nome", "usuario", "dataEvento", "?", "alfabetica"):
            with self.subTest(ordem=ordem):
                response = self.client.get(self.url, {"ordem": ordem})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["ordem"], "nome")
                self.assertEqual(
                    list(response.context["eventos"]),
                    [self.eventos[i] for i in (1, 2, 3, 0)],
                )

    def test_estado_vazio_sem_eventos(self):
        Evento.objects.all().delete()
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["eventos"], [])
        self.assertEqual(response.context["ordem"], "nome")

    def test_navegacao_exclusiva_para_autenticados(self):
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, f'href="{self.url}"')
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{self.url}"')

    def test_links_de_edicao_relativos(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        for evento in self.eventos:
            self.assertContains(response, f'href="{evento.pk}/editar/"')
