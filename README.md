# SALTY — Fase 1 (base e cardápio)

Cardápio digital mobile-first servido pelo Flask. **Não usa MySQL**: os dados são de demonstração
(`backend/demo/data.py`) e nenhum pedido é registrado nesta fase.

## Executar no Windows (PowerShell, dentro da pasta salty)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```
Abra http://127.0.0.1:5000

Se o PowerShell bloquear a ativação: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo.

## Testes
```powershell
pip install pytest
pytest
```

## Estado da Fase 1
Pronto: cardápio, categorias (filtro), detalhes e personalização com validação, carrinho (localStorage), API de leitura.
Depende de fases futuras: checkout e pedidos (Fase 2), painel admin (Fase 3), banco e autenticação (Fase 5).

## Onde trocar para MySQL depois
Somente `backend/repositories/catalog_repository.py`.
