import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
import numpy as np
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

def normalize_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    return df

def calc_regression(series, window=20):
    y = series.tail(window).values
    x = np.arange(window)
    n = len(x)
    slope = (n * np.sum(x*y) - np.sum(x)*np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
    intercept = (np.sum(y) - slope * np.sum(x)) / n
    line = slope * x + intercept
    std = np.std(y - line)
    return slope, line - 2*std, line, line + 2*std

def classify_trend(pct):
    if pct > 0.0100: return "VERY BULLISH", '#2E7D32', 5
    elif pct >= 0.0025: return "BULLISH", '#4CAF50', 4
    elif pct >= -0.0025: return "NEUTRAL", '#607D8B', 3
    elif pct >= -0.0100: return "BEARISH", '#F44336', 2
    else: return "VERY BEARISH", '#B71C1C', 1

def calculate_weighted_score(pct_1d, pct_4h, pct_1h, formula_type="intraday_local"):
    _, _, score_1d = classify_trend(pct_1d)
    _, _, score_4h = classify_trend(pct_4h)
    _, _, score_1h = classify_trend(pct_1h)
    
    formulas = {
        "intraday_local": (score_1h * 0.50) + (score_4h * 0.30) + (score_1d * 0.20),
        "intraday_mid":   (score_1h * 0.20) + (score_4h * 0.50) + (score_1d * 0.30),
        "intraday_positional": (score_1h * 0.20) + (score_4h * 0.30) + (score_1d * 0.50)
    }
    
    weighted_score = formulas.get(formula_type, formulas["intraday_local"])
    trend_mode = "bullish" if weighted_score > 3.0 else "bearish"
    return weighted_score, trend_mode, score_1d, score_4h, score_1h

def calculate_pivot_zones(df_1h, current_idx, num_zones=3):
    zones = []
    today = df_1h.index[current_idx].normalize()
    current_day_start = today
    prev_day_start = current_day_start - pd.Timedelta(days=1)
    prev_prev_day_start = prev_day_start - pd.Timedelta(days=1)
    period_starts = [prev_prev_day_start, prev_day_start, current_day_start]
    
    for i, period_start in enumerate(period_starts):
        df_period = df_1h[(df_1h.index >= period_start) & (df_1h.index < period_start + pd.Timedelta(days=1))]
        if len(df_period) == 0:
            continue
        
        is_completed = (period_start + pd.Timedelta(days=1)) <= df_1h.index[-1]
        period_high = df_period['High'].max()
        period_low = df_period['Low'].min()
        
        if is_completed:
            period_close = df_period['Close'].iloc[-1]
            future = False
        else:
            period_close = df_1h['Close'].iloc[current_idx]
            future = True
        
        PP = (period_high + period_low + period_close) / 3.0
        R1 = 2 * PP - period_low
        R2 = PP + (period_high - period_low)
        S1 = 2 * PP - period_high
        S2 = PP - (period_high - period_low)
        M2 = 0.5 * (PP + S1)
        M3 = 0.5 * (PP + R1)
        M4 = 0.5 * (R1 + R2)
        M5 = 0.5 * (S1 + S2)
        
        if future:
            zone_mid_bull = (PP + M2) / 2
            risk_distance_bull = M4 - zone_mid_bull
            stop_loss_bull = zone_mid_bull - (risk_distance_bull / 2)
            zone_mid_bear = (PP + M3) / 2
            risk_distance_bear = zone_mid_bear - M5
            stop_loss_bear = zone_mid_bear + (risk_distance_bear / 2)
            risk_reward_ratio = 2.0
        else:
            stop_loss_bull = None
            stop_loss_bear = None
            risk_reward_ratio = None
        
        zones.append({
            'start_time': period_start,
            'end_time': period_start + pd.Timedelta(days=1),
            'PP': PP,
            'R1': R1,
            'R2': R2,
            'S1': S1,
            'S2': S2,
            'M2': M2,
            'M3': M3,
            'M4': M4,
            'M5': M5,
            'period_high': period_high,
            'period_low': period_low,
            'period_close': period_close,
            'is_completed': is_completed,
            'future': future,
            'zone_index': i,
            'bars_count': len(df_period),
            'stop_loss_bull': stop_loss_bull,
            'stop_loss_bear': stop_loss_bear,
            'risk_reward_ratio': risk_reward_ratio
        })
    
    return zones

def generate_chart(df_1h, name, ticker, formula_type="intraday_local"):
    if not isinstance(df_1h.index, pd.DatetimeIndex):
        df_1h.index = pd.to_datetime(df_1h.index)
    
    if df_1h.index.tz is None:
        df_1h.index = df_1h.index.tz_localize('UTC')
    df_1h.index = df_1h.index.tz_convert('Europe/Moscow')
    
    df_4h = df_1h.resample('4h').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    df_1d = df_1h.resample('D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    slope_1h, lower_1h, mid_1h, upper_1h = calc_regression(df_1h['Close'])
    slope_4h, lower_4h, mid_4h, upper_4h = calc_regression(df_4h['Close'])
    slope_1d, lower_1d, mid_1d, upper_1d = calc_regression(df_1d['Close'])
    
    cur = df_1h['Close'].iloc[-1]
    pct_1h = (slope_1h / cur) * 100
    pct_4h = ((slope_4h / df_4h['Close'].iloc[-1]) * 100) / 4.0
    pct_1d = ((slope_1d / df_1d['Close'].iloc[-1]) * 100) / 24.0
    
    weighted_score, trend_mode, score_1d, score_4h, score_1h = calculate_weighted_score(
        pct_1d, pct_4h, pct_1h, formula_type
    )
    
    if trend_mode == "bullish":
        cat_1d, col_1d, _ = classify_trend(pct_1d)
        cat_4h, col_4h, _ = classify_trend(pct_4h)
        cat_1h, col_1h, _ = classify_trend(pct_1h)
        zone_color = '#C8E6C9'
        zone_edge = '#4CAF50'
        target_color = '#546E7A'
        stop_color = '#D32F2F'
        zone_label = "Buy Zone"
    else:
        cat_1d, col_1d, _ = classify_trend(pct_1d)
        cat_4h, col_4h, _ = classify_trend(pct_4h)
        cat_1h, col_1h, _ = classify_trend(pct_1h)
        zone_color = '#FFEBEE'
        zone_edge = '#F44336'
        target_color = '#546E7A'
        stop_color = '#D32F2F'
        zone_label = "Sell Zone"
    
    plot_window = 100
    future_hours = 30
    total_width = plot_window + future_hours + 8
    df_plot = df_1h.tail(plot_window).copy()
    
    fig, ax = plt.subplots(figsize=(22, 10), facecolor='white')
    ax.set_facecolor('#F8F9FA')
    
    for i, (_, row) in enumerate(df_plot.iterrows()):
        o, c, h, l = row['Open'], row['Close'], row['High'], row['Low']
        clr = '#26A69A' if c >= o else '#EF5350'
        ax.bar(i, abs(c-o), bottom=min(o,c), width=0.8, color=clr, edgecolor='black', linewidth=0.8)
        ax.plot([i,i], [h, max(o,c)], color='black', linewidth=1)
        ax.plot([i,i], [min(o,c), l], color='black', linewidth=1)
    
    pivots = calculate_pivot_zones(df_1h, len(df_1h)-1, num_zones=3)
    
    if len(df_1d) >= 20:
        x = np.linspace(max(0, plot_window-96), plot_window, 5)
        y_mid = np.linspace(mid_1d[-4], mid_1d[-1], 5)
        y_up = np.linspace(upper_1d[-4], upper_1d[-1], 5)
        y_low = np.linspace(lower_1d[-4], lower_1d[-1], 5)
        ax.plot(x, y_mid, color=col_1d, linewidth=2.8, alpha=0.9)
        ax.fill_between(x, y_low, y_up, color=col_1d, alpha=0.08)
    
    if len(df_4h) >= 20:
        x = np.linspace(max(0, plot_window-80), plot_window, 21)
        y_mid = np.interp(x, np.linspace(max(0, plot_window-80), plot_window, 20), mid_4h[-20:])
        y_up = np.interp(x, np.linspace(max(0, plot_window-80), plot_window, 20), upper_4h[-20:])
        y_low = np.interp(x, np.linspace(max(0, plot_window-80), plot_window, 20), lower_4h[-20:])
        ax.plot(x, y_mid, color=col_4h, linewidth=2.6, alpha=0.95)
        ax.fill_between(x, y_low, y_up, color=col_4h, alpha=0.12)
    
    if len(df_1h) >= 20:
        x = np.arange(plot_window-20, plot_window)
        ax.plot(x, mid_1h[-20:], color=col_1h, linewidth=3.2, alpha=1.0, marker='o', markersize=4)
        ax.fill_between(x, lower_1h[-20:], upper_1h[-20:], color=col_1h, alpha=0.20)
    
    if pivots:
        zone_width = 24
        for i, zone in enumerate(pivots):
            if zone['future']:
                x_start = plot_window + 2
                x_end = x_start + zone_width
                label_x = x_end + 1.8
                zone_name = "Projected"
                zone_alpha = 0.65
                info_alpha = 0.90
            else:
                zone_pos = i
                x_start = plot_window - zone_width * (2 - zone_pos) - 2
                x_end = x_start + zone_width
                label_x = x_start + 1.8
                zone_name = f"Zone {zone_pos + 1}"
                zone_alpha = 0.35
                info_alpha = 0.75
            
            if trend_mode == "bullish":
                zone_bottom = zone['M2']
                zone_top = zone['PP']
                target_conservative = zone['M4']
                target_aggressive = zone['R2']
                target1_label = f"M4\n{target_conservative:.2f}"
                target2_label = f"R2\n{target_aggressive:.2f}"
                
                if zone['future']:
                    zone_mid = (zone_top + zone_bottom) / 2
                    risk_distance = target_conservative - zone_mid
                    stop_loss = zone_mid - (risk_distance / 2)
                    rr_ratio = 2.0
                else:
                    stop_loss = None
                    rr_ratio = None
            else:
                zone_bottom = zone['PP']
                zone_top = zone['M3']
                target_conservative = zone['M5']
                target_aggressive = zone['S2']
                target1_label = f"M5\n{target_conservative:.2f}"
                target2_label = f"S2\n{target_aggressive:.2f}"
                
                if zone['future']:
                    zone_mid = (zone_top + zone_bottom) / 2
                    risk_distance = zone_mid - target_conservative
                    stop_loss = zone_mid + (risk_distance / 2)
                    rr_ratio = 2.0
                else:
                    stop_loss = None
                    rr_ratio = None
            
            rect = Rectangle((x_start, zone_bottom), x_end - x_start, zone_top - zone_bottom,
                             linewidth=1.6, edgecolor=zone_edge, facecolor=zone_color, 
                             alpha=zone_alpha, linestyle='--', zorder=3)
            ax.add_patch(rect)
            
            target_line_width = zone_width * 0.82
            start_x = x_start + (zone_width - target_line_width) / 2
            
            ax.plot([start_x, start_x + target_line_width], [target_aggressive, target_aggressive], 
                    color=target_color, linewidth=1.7, linestyle=':', alpha=0.80, zorder=4)
            ax.plot([start_x, start_x + target_line_width], [target_conservative, target_conservative], 
                    color=target_color, linewidth=1.7, linestyle=':', alpha=0.80, zorder=4)
            
            if zone['future'] and stop_loss is not None:
                ax.plot([start_x, start_x + target_line_width], [stop_loss, stop_loss], 
                        color=stop_color, linewidth=2.0, linestyle='--', alpha=0.85, zorder=5)
            
            if trend_mode == "bullish":
                ax.text(label_x, target_aggressive, target2_label, fontsize=8.5, color=target_color, 
                        va='bottom', ha='left', fontweight='medium')
                ax.text(label_x, target_conservative, target1_label, fontsize=8.5, color=target_color, 
                        va='bottom', ha='left', fontweight='medium')
            else:
                ax.text(label_x, target_aggressive, target2_label, fontsize=8.5, color=target_color, 
                        va='top', ha='left', fontweight='medium')
                ax.text(label_x, target_conservative, target1_label, fontsize=8.5, color=target_color, 
                        va='top', ha='left', fontweight='medium')
            
            ax.text(label_x, zone['PP'], f'PP\n{zone["PP"]:.2f}', fontsize=8.5, color=zone_edge, 
                    va='center', ha='left', fontweight='bold')
            
            zone_label_text = f"{zone_name} {zone_label}"
            ax.text(x_start + zone_width/2, zone_top * (0.995 if trend_mode == "bullish" else 1.005), 
                    zone_label_text, fontsize=8, color=zone_edge, ha='center', 
                    va='top' if trend_mode == "bullish" else 'bottom', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, 
                             edgecolor=zone_edge, linewidth=1.0))
            
            if zone['future']:
                if trend_mode == "bullish" and stop_loss is not None:
                    info_text = (f"{zone['bars_count']}h bars\n"
                                f"H:{zone['period_high']:.2f} L:{zone['period_low']:.2f}\n"
                                f"C:{zone['period_close']:.2f}\n"
                                f"SL:{stop_loss:.2f} RR 1:2")
                elif trend_mode == "bearish" and stop_loss is not None:
                    info_text = (f"{zone['bars_count']}h bars\n"
                                f"H:{zone['period_high']:.2f} L:{zone['period_low']:.2f}\n"
                                f"C:{zone['period_close']:.2f}\n"
                                f"SL:{stop_loss:.2f} RR 1:2")
                else:
                    info_text = (f"{zone['bars_count']}h bars\n"
                                f"H:{zone['period_high']:.2f} L:{zone['period_low']:.2f}\n"
                                f"C:{zone['period_close']:.2f}")
            else:
                info_text = (f"Completed\n"
                            f"H:{zone['period_high']:.2f} L:{zone['period_low']:.2f}\n"
                            f"C:{zone['period_close']:.2f}")
            
            ax.text(x_start + zone_width/2, zone_bottom * (1.005 if trend_mode == "bullish" else 0.995), 
                    info_text, fontsize=7, color='#37474F', ha='center', 
                    va='bottom' if trend_mode == "bullish" else 'top',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=info_alpha, 
                             edgecolor='#E0E0E0', linewidth=0.7))
    
    ax.set_title(f'{name} ({ticker}) -- Multi-Timeframe Trend + Pivot Zones | Score: {weighted_score:.2f} ({trend_mode.capitalize()})', 
                 fontsize=22, fontweight='bold', pad=20, color='#263238')
    ax.set_ylabel('Price', fontsize=14, fontweight='bold', labelpad=12, color='#37474F')
    ax.set_xlabel('Time (MSK)', fontsize=14, fontweight='bold', labelpad=12, color='#37474F')
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.7)
    
    x_ticks = np.arange(0, total_width, 12)
    x_labels = []
    for i in x_ticks:
        if i < plot_window and i < len(df_plot):
            x_labels.append(df_plot.index[int(i)].strftime('%m-%d %H:%M'))
        elif i >= plot_window:
            hours_ahead = int(i - plot_window)
            if hours_ahead == 0:
                x_labels.append("Now")
            else:
                x_labels.append(f"+{hours_ahead}h")
        else:
            x_labels.append("")
    
    ax.set_xticks(x_ticks[:len(x_labels)])
    ax.set_xticklabels(x_labels, rotation=35, ha='right', fontsize=9, color='#37474F')
    ax.set_xlim(-3, total_width)
    
    trend_text = f"""DAILY (20d):   {cat_1d:<15} score={score_1d}
4H (20x4h):    {cat_4h:<15} score={score_4h}
1H (20h):      {cat_1h:<15} score={score_1h}
WEIGHTED:      {weighted_score:.2f} ({trend_mode.capitalize()})"""
    bbox = dict(boxstyle='round,pad=0.8', facecolor='white', alpha=0.92, edgecolor='#E0E0E0', linewidth=1.0)
    ax.text(0.02, 0.98, trend_text, transform=ax.transAxes, fontsize=11.5, fontweight='bold',
            verticalalignment='top', family='monospace', color='#263238', bbox=bbox)
    
    period = f"{df_plot.index[0].strftime('%d %b %Y %H:%M')} -> {df_plot.index[-1].strftime('%d %b %Y %H:%M')} MSK"
    ax.text(0.98, 0.02, period, transform=ax.transAxes, fontsize=9.5, color='gray', ha='right', 
            style='italic', alpha=0.85)
    
    plt.tight_layout()
    
    chart_data = {
        'name': name,
        'ticker': ticker,
        'weighted_score': weighted_score,
        'trend_mode': trend_mode,
        'formula_type': formula_type,
        'scores': {
            '1d': score_1d,
            '4h': score_4h,
            '1h': score_1h
        }
    }
    
    if pivots and pivots[-1]['future']:
        last_zone = pivots[-1]
        if trend_mode == "bullish" and last_zone['stop_loss_bull'] is not None:
            zone_mid = (last_zone['PP'] + last_zone['M2']) / 2
            sl = last_zone['stop_loss_bull']
            target = last_zone['M4']
            chart_data['stop_loss'] = sl
            chart_data['entry_mid'] = zone_mid
            chart_data['target'] = target
            chart_data['rr_ratio'] = 2.00
        elif trend_mode == "bearish" and last_zone['stop_loss_bear'] is not None:
            zone_mid = (last_zone['PP'] + last_zone['M3']) / 2
            sl = last_zone['stop_loss_bear']
            target = last_zone['M5']
            chart_data['stop_loss'] = sl
            chart_data['entry_mid'] = zone_mid
            chart_data['target'] = target
            chart_data['rr_ratio'] = 2.00
    
    return fig, chart_data