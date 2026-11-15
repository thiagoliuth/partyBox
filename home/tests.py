from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
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
        self.assertContains(response, "Você ainda não cadastrou eventos.")
        self.assertContains(response, "data-evento-open")

    def test_navegacao_exclusiva_para_autenticados(self):
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, f'href="{self.url}"')
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{self.url}"')

    def test_links_de_edicao(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        for evento in self.eventos:
            self.assertContains(response, f'href="{reverse("editar_evento", args=[evento.pk])}"')

    def test_opcao_de_ordenacao_selecionada(self):
        self.client.force_login(self.usuario)
        for ordem, esperado in (("nome", "nome"), ("data", "data"), ("invalida", "nome")):
            with self.subTest(ordem=ordem):
                response = self.client.get(self.url, {"ordem": ordem})
                self.assertRegex(
                    response.content.decode(),
                    rf'<option\s+value="{esperado}"\s+selected(?:="selected")?\s*>',
                )

    def test_html_nao_expoe_eventos_de_outro_usuario_nem_com_pk_injetado(self):
        outro = Evento.objects.create(
            usuario=self.outro_usuario, nome="Evento secreto de outro dono",
            dataEvento="2030-12-01", horarioEvento="12:00",
        )
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"pk": outro.pk, "usuario": self.outro_usuario.pk})
        self.assertNotContains(response, outro.nome)
        self.assertEqual(set(response.context["eventos"]), set(self.eventos))


class EdicaoEventoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="editor", email="editor@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="intruso", email="intruso@example.com", password="senha-teste"
        )
        cls.evento = Evento.objects.create(
            usuario=cls.usuario, nome="Original", descricao="Descrição original",
            dataEvento="2030-12-01", horarioEvento="18:30", siglaEstado="SP",
            cidade="São Paulo", bairro="Centro", rua="Rua original", numero="10",
            cupom_codigo="ANTES", cupom_descricao="Desconto original",
        )

    def setUp(self):
        self.editar = reverse("editar_evento", args=[self.evento.pk])
        self.excluir = reverse("excluir_evento", args=[self.evento.pk])
        self.dados = {
            f"editar-{campo}": valor for campo, valor in {
                "nome": "Atualizado", "descricao": "Nova descrição",
                "dataEvento": "2031-02-03", "horarioEvento": "09:15",
                "siglaEstado": "RJ", "cidade": "Rio de Janeiro", "bairro": "Novo",
                "rua": "Nova rua", "numero": "20", "ehPublico": "on",
                "cupom_codigo": "NOVO", "cupom_descricao": "Novo desconto",
            }.items()
        }

    def assertEventoInalterado(self):
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.nome, "Original")
        self.assertEqual(self.evento.usuario, self.usuario)
        self.assertEqual(self.evento.cupom_codigo, "ANTES")

    def test_anonimos_get_e_post_nas_tres_rotas_exigem_login(self):
        for url in (reverse("meus_eventos"), self.editar, self.excluir):
            for metodo in ("get", "post"):
                with self.subTest(url=url, metodo=metodo):
                    response = getattr(self.client, metodo)(url)
                    self.assertRedirects(
                        response, f"{reverse('admin:login')}?next={url}",
                        fetch_redirect_response=False,
                    )
        self.assertEventoInalterado()

    def test_get_dono_formulario_preenchido_com_prefixo_e_data_iso(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.editar)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/editar_evento.html")
        form = response.context["form"]
        self.assertEqual(response.context["evento"], self.evento)
        self.assertEqual(form.prefix, "editar")
        self.assertEqual(form["nome"].value(), "Original")
        self.assertIn('name="editar-nome"', str(form["nome"]))
        self.assertIn('id="id_editar-nome"', str(form["nome"]))
        self.assertIn('value="2030-12-01"', str(form["dataEvento"]))
        self.assertIn('value="18:30"', str(form["horarioEvento"]))
        self.assertNotIn("usuario", form.fields)

    def test_post_valido_atualiza_campos_preserva_dono_e_mostra_sucesso(self):
        self.client.force_login(self.usuario)
        self.dados.update({"editar-usuario": self.outro_usuario.pk, "usuario": self.outro_usuario.pk})
        response = self.client.post(self.editar, self.dados)
        self.assertRedirects(response, reverse("meus_eventos"))
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.usuario, self.usuario)
        for campo in ("nome", "descricao", "siglaEstado", "cidade", "bairro", "rua",
                      "numero", "cupom_codigo", "cupom_descricao"):
            self.assertEqual(getattr(self.evento, campo), self.dados[f"editar-{campo}"])
        self.assertEqual(self.evento.dataEvento.isoformat(), "2031-02-03")
        self.assertEqual(self.evento.horarioEvento.isoformat(), "09:15:00")
        self.assertTrue(any(m.level == messages.SUCCESS for m in get_messages(response.wsgi_request)))

    def test_post_invalido_mostra_erros_sem_mutacao(self):
        self.client.force_login(self.usuario)
        self.dados["editar-nome"] = ""
        response = self.client.post(self.editar, self.dados)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/editar_evento.html")
        self.assertIn("nome", response.context["form"].errors)
        self.assertTrue(response.context["form"].is_bound)
        self.assertEventoInalterado()

    def test_dono_exclui_por_post_com_redirecionamento_e_sucesso(self):
        self.client.force_login(self.usuario)
        response = self.client.post(self.excluir)
        self.assertRedirects(response, reverse("meus_eventos"))
        self.assertFalse(Evento.objects.filter(pk=self.evento.pk).exists())
        self.assertTrue(any(m.level == messages.SUCCESS for m in get_messages(response.wsgi_request)))

    def test_exclusao_rejeita_metodos_diferentes_de_post(self):
        self.client.force_login(self.usuario)
        for metodo in ("get", "put", "patch", "delete", "head", "options"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.excluir)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], "POST")
                self.assertEventoInalterado()

    def test_outro_usuario_recebe_404_sem_mutacao(self):
        self.client.force_login(self.outro_usuario)
        for metodo, url in (("get", self.editar), ("post", self.editar), ("post", self.excluir)):
            with self.subTest(metodo=metodo, url=url):
                response = getattr(self.client, metodo)(url, self.dados if metodo == "post" else {})
                self.assertEqual(response.status_code, 404)
                self.assertEventoInalterado()

    def test_pk_inexistente_recebe_404(self):
        self.client.force_login(self.usuario)
        for metodo, nome in (("get", "editar_evento"), ("post", "editar_evento"),
                             ("post", "excluir_evento")):
            with self.subTest(metodo=metodo, nome=nome):
                response = getattr(self.client, metodo)(
                    reverse(nome, args=[self.evento.pk + 1000]),
                    self.dados if metodo == "post" else {},
                )
                self.assertEqual(response.status_code, 404)
        self.assertEventoInalterado()

    def test_exclusao_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        response = client.post(self.excluir)
        self.assertEqual(response.status_code, 403)
        self.assertEventoInalterado()
