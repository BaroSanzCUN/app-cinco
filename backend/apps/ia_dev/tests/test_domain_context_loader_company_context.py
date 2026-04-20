from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.ia_dev.application.delegation.domain_context_loader import DomainContextLoader


class _FakeStore:
    @staticmethod
    def get_contexto_compania(*, codigo_compania: str = "CINCO") -> dict:
        return {
            "codigo_compania": codigo_compania,
            "nombre_compania": "Compania Demo",
            "dominios_oficiales": ["empleados", "ausentismo", "transporte"],
            "dominios_operativos": ["empleados", "ausentismo"],
        }

    @staticmethod
    def list_dominios(*, limit: int = 300) -> list[dict]:
        return []


class DomainContextLoaderCompanyContextTests(SimpleTestCase):
    def test_load_all_attaches_company_context_to_each_domain(self):
        with TemporaryDirectory() as tmp:
            registry_dir = Path(tmp)
            (registry_dir / "empleados.domain.yaml").write_text(
                "\n".join(
                    [
                        "dominio: empleados",
                        "nombre_dominio: Empleados",
                        "estado_dominio: active",
                    ]
                ),
                encoding="utf-8",
            )
            (registry_dir / "ausentismo.domain.yaml").write_text(
                "\n".join(
                    [
                        "dominio: ausentismo",
                        "nombre_dominio: Ausentismo",
                        "estado_dominio: active",
                    ]
                ),
                encoding="utf-8",
            )
            loader = DomainContextLoader(registry_dir=registry_dir, store=_FakeStore())
            contexts = loader.load_all()

        self.assertIn("empleados", contexts)
        self.assertIn("ausentismo", contexts)
        self.assertEqual(
            str((contexts["empleados"].get("company_context") or {}).get("codigo_compania") or ""),
            "CINCO",
        )
        self.assertEqual(
            list((contexts["ausentismo"].get("company_context") or {}).get("dominios_operativos") or []),
            ["empleados", "ausentismo"],
        )

    def test_load_from_files_merges_contexto_reglas_y_ejemplos(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            registry_dir = base_dir / "registry"
            registry_dir.mkdir(parents=True, exist_ok=True)
            domain_dir = base_dir / "empleados"
            domain_dir.mkdir(parents=True, exist_ok=True)
            (registry_dir / "empleados.domain.yaml").write_text(
                "\n".join(
                    [
                        "dominio: empleados",
                        "nombre_dominio: Empleados",
                        "estado_dominio: active",
                        "tablas_asociadas:",
                        "  - table_name: cinco_base_de_personal",
                    ]
                ),
                encoding="utf-8",
            )
            (domain_dir / "contexto.yaml").write_text(
                "\n".join(
                    [
                        "contexto_agente:",
                        "  descripcion: Dominio de personal interno",
                        "vocabulario_negocio:",
                        "  - personal",
                        "tablas_prioritarias:",
                        "  - cinco_base_de_personal",
                    ]
                ),
                encoding="utf-8",
            )
            (domain_dir / "reglas.yaml").write_text(
                "\n".join(
                    [
                        "reglas_negocio:",
                        "  - codigo: empleados_estado_por_defecto",
                        "    descripcion: Usar ACTIVO por defecto",
                    ]
                ),
                encoding="utf-8",
            )
            (domain_dir / "ejemplos.yaml").write_text(
                "\n".join(
                    [
                        "ejemplos_consulta:",
                        "  - consulta: empleados por cargo",
                        "    capacidad_esperada: empleados.count.active.v1",
                    ]
                ),
                encoding="utf-8",
            )
            loader = DomainContextLoader(registry_dir=registry_dir, store=_FakeStore())
            loader.domains_dir = base_dir
            contexts = loader.load_from_files()

        payload = dict(contexts.get("empleados") or {})
        self.assertEqual(str((payload.get("contexto_agente") or {}).get("descripcion") or ""), "Dominio de personal interno")
        self.assertEqual(list(payload.get("vocabulario_negocio") or []), ["personal"])
        self.assertEqual(list(payload.get("tablas_prioritarias") or []), ["cinco_base_de_personal"])
        self.assertEqual(str(((payload.get("reglas_negocio") or [{}])[0]).get("codigo") or ""), "empleados_estado_por_defecto")
        self.assertEqual(str(((payload.get("ejemplos_consulta") or [{}])[0]).get("consulta") or ""), "empleados por cargo")
