from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import base64
from io import BytesIO
from datetime import datetime
import traceback

from .utils import normalize_df, generate_chart
from .trend_dashboard import generate_trend_dashboard
import yfinance as yf
import pandas as pd

app = FastAPI(title="Pivot Screener")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ALL_ASSETS = [
    {"name": "S&P 500", "ticker": "SPY", "category": "Stocks"},
    {"name": "Hang Seng", "ticker": "HSI=F", "category": "Stocks"},
    {"name": "NASDAQ", "ticker": "QQQ", "category": "Stocks"},
    {"name": "EURO STOXX 50", "ticker": "FEZ", "category": "Stocks"},
    {"name": "MSCI WORLD", "ticker": "URTH", "category": "Stocks"},
    {"name": "Bitcoin", "ticker": "BTC-USD", "category": "Crypto"},
    {"name": "Ethereum", "ticker": "ETH-USD", "category": "Crypto"},
    {"name": "Solana", "ticker": "SOL-USD", "category": "Crypto"},
    {"name": "Gold", "ticker": "GC=F", "category": "Metals"},
    {"name": "Silver", "ticker": "SI=F", "category": "Metals"},
    {"name": "Platinum", "ticker": "PL=F", "category": "Metals"},
    {"name": "Palladium", "ticker": "PA=F", "category": "Metals"},
    {"name": "Copper", "ticker": "HG=F", "category": "Metals"},
    {"name": "Brent", "ticker": "BZ=F", "category": "Energy"},
    {"name": "Natural Gas US", "ticker": "NG=F", "category": "Energy"},
    {"name": "DXY", "ticker": "^DX-Y.NYB", "category": "Forex"},
]

FORMULA_TYPES = {
    "intraday_local": "Intoday (local trend) = 1h*0.50 + 4h*0.30 + 1d*0.20",
    "intraday_mid": "Intoday (mid-term) = 1h*0.20 + 4h*0.50 + 1d*0.30",
    "intraday_positional": "Intoday (positional) = 1h*0.20 + 4h*0.30 + 1d*0.50"
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    assets_by_category = {}
    for asset in ALL_ASSETS:
        category = asset['category']
        if category not in assets_by_category:
            assets_by_category[category] = []
        assets_by_category[category].append(asset)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "assets_by_category": assets_by_category,
        "formula_types": FORMULA_TYPES,
        "default_formula": "intraday_local"
    })

@app.post("/generate", response_class=HTMLResponse)
async def generate_charts(
    request: Request,
    selected_assets: list = Form(default=[]),
    formula_type: str = Form(default="intraday_local")
):
    if not selected_assets:
        return await index(request)
    
    selected_assets_list = [a for a in ALL_ASSETS if a['ticker'] in selected_assets]
    charts = []
    errors = []
    
    for asset in selected_assets_list:
        try:
            df = normalize_df(yf.download(asset['ticker'], period="730d", interval="1h", progress=False))
            
            if len(df) < 50:
                errors.append(f"{asset['name']} ({asset['ticker']}): insufficient data")
                continue
            
            fig, chart_data = generate_chart(df, asset['name'], asset['ticker'], formula_type)
            
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
            import matplotlib.pyplot as plt
            plt.close(fig)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            charts.append({
                'data': chart_data,
                'image': img_base64
            })
            
        except Exception as e:
            error_detail = traceback.format_exc()
            errors.append(f"{asset['name']} ({asset['ticker']}): {str(e)}")
            errors.append(f"  Traceback: {error_detail[:200]}")
            continue
    
    assets_by_category = {}
    for asset in ALL_ASSETS:
        category = asset['category']
        if category not in assets_by_category:
            assets_by_category[category] = []
        assets_by_category[category].append(asset)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "assets_by_category": assets_by_category,
        "formula_types": FORMULA_TYPES,
        "selected_assets": selected_assets,
        "selected_formula": formula_type,
        "charts": charts,
        "errors": errors,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.post("/generate_trends", response_class=HTMLResponse)
async def generate_trends_dashboard(
    request: Request,
    selected_assets: list = Form(default=[]),
    formula_type: str = Form(default="intraday_local")
):
    """Генерация дашборда трендов на основе скользящих средних"""
    
    if not selected_assets:
        return await index(request)
    
    selected_assets_list = [a for a in ALL_ASSETS if a['ticker'] in selected_assets]
    errors = []
    
    try:
        # Генерация дашборда трендов
        dashboard_data = generate_trend_dashboard(selected_assets_list)
    except Exception as e:
        errors.append(f"Ошибка генерации дашборда: {str(e)}")
        errors.append(f"Traceback: {traceback.format_exc()[:200]}")
        dashboard_data = []
    
    # Группируем активы по категориям для повторного отображения формы
    assets_by_category = {}
    for asset in ALL_ASSETS:
        category = asset['category']
        if category not in assets_by_category:
            assets_by_category[category] = []
        assets_by_category[category].append(asset)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "assets_by_category": assets_by_category,
        "formula_types": FORMULA_TYPES,
        "selected_assets": selected_assets,
        "selected_formula": formula_type,
        "dashboard_data": dashboard_data,  # Передаем данные дашборда
        "errors": errors,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)