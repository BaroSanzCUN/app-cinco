#!/usr/bin/env python
"""
Script para generar una SECRET_KEY segura para Django.
Uso: python generate_secret_key.py
"""

from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("\n" + "="*70)
    print("🔑 DJANGO SECRET_KEY generada:")
    print("="*70)
    print(f"\n{secret_key}\n")
    print("="*70)
    print("\nCopia esta clave y agrégala a tu archivo .env:")
    print(f"DJANGO_SECRET_KEY={secret_key}")
    print("\n⚠️  IMPORTANTE: Nunca compartas esta clave ni la subas al repositorio!\n")
