import tkinter as tk
import customtkinter as ctk
import traceback
import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from live.trader_okx import OKXTrader
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message="Glyph .* missing from font")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TradingGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Crypto TA Analyzer - 合约激进策略仪表盘")
        self.geometry("1200x900")
        self.minsize(1000, 800)

        # 全局字体设置
        self.font_title = ("Microsoft YaHei UI", 28, "bold")
        self.font_label = ("Microsoft YaHei UI", 16, "bold")
        self.font_normal = ("Microsoft YaHei UI", 14)
        self.font_input = ("Microsoft YaHei UI", 13)
        self.font_text = ("Consolas", 13)
        self.font_button = ("Microsoft YaHei UI", 14, "bold")

        self.config = load_config('aggressive.yaml')
        api_cfg = self.config.get('api', {})
        if not api_cfg.get('key'):
            ctk.CTkLabel(self, text="错误：config.yaml 缺少 api 节！", text_color="red", font=self.font_title).pack(pady=50)
            return

        self.trader = OKXTrader(api_cfg['key'], api_cfg['secret'], api_cfg['passphrase'], api_cfg.get('use_demo', True))

        # 永续合约专用设置
        self.symbol = 'BTC/USDT:USDT'  # 永续合约
        self.timeframe = '30m'         # ccxt标准格式 '30m'
        self.leverage = 10             # 默认杠杆

        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.sl_price = 0
        self.tp_price = 0

        self.after_id = None

        # 自动下单开关（默认开启）
        self.auto_trade_enabled = True

        # 主滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=20)
        scroll_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 标题
        ctk.CTkLabel(scroll_frame, text="永续合约激进策略实时仪表盘", font=self.font_title).pack(pady=(20, 10))
        ctk.CTkLabel(scroll_frame, text="支持多空双向 + 杠杆调节 + 自动下单开关（Demo盘安全测试）", 
                     text_color="#1f6aa5", font=self.font_normal).pack(pady=(0, 30))

        # 参数调整区（Tabview）
        tabview = ctk.CTkTabview(scroll_frame, height=500)
        tabview.pack(fill='x', padx=20, pady=10)

        tab_contract = tabview.add("合约参数")
        tab_risk = tabview.add("风险与仓位参数")
        tab_indicators = tabview.add("指标参数")
        tab_patterns = tabview.add("形态检测参数")

        # 合约参数Tab
        ctk.CTkLabel(tab_contract, text="杠杆调节（1-20x）", font=self.font_label).pack(pady=(20,10))
        self.leverage_var = tk.IntVar(value=10)
        leverage_slider = ctk.CTkSlider(tab_contract, from_=1, to=20, number_of_steps=19,
                                       variable=self.leverage_var, width=400)
        leverage_slider.pack(pady=10)
        ctk.CTkLabel(tab_contract, textvariable=self.leverage_var, font=self.font_normal).pack()

        ctk.CTkButton(tab_contract, text="应用杠杆", command=self.apply_leverage_button, 
                      height=45, font=self.font_button, width=200).pack(pady=20)

        self.current_leverage_label = ctk.CTkLabel(tab_contract, text="当前杠杆: 未设置", font=self.font_normal)
        self.current_leverage_label.pack(pady=10)

        # 自动下单开关
        ctk.CTkLabel(tab_contract, text="自动下单开关", font=self.font_label).pack(pady=(30,10))
        self.auto_trade_switch = ctk.CTkSwitch(tab_contract, text="自动下单：开启", font=self.font_normal,
                                               command=self.toggle_auto_trade)
        self.auto_trade_switch.select()
        self.auto_trade_switch.pack(pady=10)

        self.auto_trade_status_label = ctk.CTkLabel(tab_contract, text="自动下单：已开启", font=self.font_normal, text_color="#00ff00")
        self.auto_trade_status_label.pack(pady=5)

        # 风险参数
        self.refresh_interval_var = self.create_input(tab_risk, "自动刷新间隔 (秒):", 60)
        self.risk_var = self.create_input(tab_risk, "单笔风险 %:", 1.5)
        self.atr_var = self.create_input(tab_risk, "ATR止损倍数:", 2.5)
        self.rr_var = self.create_input(tab_risk, "风险回报比 (TP倍数):", 3.5)
        self.order_size_var = self.create_input(tab_risk, "固定下单张数 (合约):", 0.001)

        # 指标/形态参数
        self.rsi_period_var = self.create_input(tab_indicators, "RSI周期:", 14)
        self.rsi_ob_var = self.create_input(tab_indicators, "RSI超买阈值:", 80)
        self.rsi_os_var = self.create_input(tab_indicators, "RSI超卖阈值:", 20)
        self.atr_period_var = self.create_input(tab_indicators, "ATR周期:", 14)
        self.ema_short_var = self.create_input(tab_indicators, "短期EMA周期:", 20)
        self.ema_long_var = self.create_input(tab_indicators, "长期EMA周期:", 50)
        self.ema_very_long_var = self.create_input(tab_indicators, "超长EMA周期:", 200)

        self.candle_lookback_var = self.create_input(tab_patterns, "蜡烛形态检测范围 (根K线):", 5)
        self.chart_pattern_lookback_var = self.create_input(tab_patterns, "图表形态检测范围 (根K线):", 50)
        self.divergence_lookback_var = self.create_input(tab_patterns, "背离检测范围 (根K线):", 30)
        self.volume_spike_threshold_var = self.create_input(tab_patterns, "放量阈值倍数:", 2.0)
        self.gap_min_pct_var = self.create_input(tab_patterns, "最小跳空幅度 %:", 0.5)

        # 按钮区
        button_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        ctk.CTkButton(button_frame, text="应用所有参数并刷新", command=self.apply_params, height=45, font=self.font_button, width=280).pack(side='left', padx=20)
        ctk.CTkButton(button_frame, text="手动刷新", command=self.manual_refresh, height=45, font=self.font_button, width=200).pack(side='left', padx=20)
        ctk.CTkButton(button_frame, text="查询持仓/余额", command=self.query_balance_pos, height=45, font=self.font_button, width=200).pack(side='left', padx=20)

        # 持仓与实时分析区
        analysis_frame = ctk.CTkFrame(scroll_frame, corner_radius=15)
        analysis_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ctk.CTkLabel(analysis_frame, text="实时持仓与信号分析（永续合约）", font=self.font_label).pack(anchor='w', padx=30, pady=(30,15))

        self.balance_label = ctk.CTkLabel(analysis_frame, text="余额: 加载中...", font=self.font_normal)
        self.balance_label.pack(anchor='w', padx=30, pady=8)

        self.pos_label = ctk.CTkLabel(analysis_frame, text="持仓方向: 空仓", font=self.font_normal)
        self.pos_label.pack(anchor='w', padx=30, pady=8)

        self.entry_label = ctk.CTkLabel(analysis_frame, text="入场时间/价格: -", font=self.font_normal)
        self.entry_label.pack(anchor='w', padx=30, pady=8)

        self.sl_tp_label = ctk.CTkLabel(analysis_frame, text="止损 / 止盈: -", font=self.font_normal)
        self.sl_tp_label.pack(anchor='w', padx=30, pady=8)

        self.pnl_label = ctk.CTkLabel(analysis_frame, text="当前盈亏: 0 USDT", font=("Microsoft YaHei UI", 20, "bold"))
        self.pnl_label.pack(anchor='w', padx=30, pady=15)

        # 详细分析文本框
        ctk.CTkLabel(analysis_frame, text="当前信号详细分析（依据最新K线，多因子动态生成）", font=self.font_label).pack(anchor='w', padx=30, pady=(30,10))
        self.analysis_text = ctk.CTkTextbox(analysis_frame, height=400, font=self.font_text)
        self.analysis_text.pack(fill='both', expand=True, padx=30, pady=10)
        self.analysis_text.insert("end", "正在加载数据...\n")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.after(2000, lambda: self.apply_leverage(self.leverage))

        self.update_data()

    def create_input(self, parent, label, default):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=10, fill='x', padx=30)
        ctk.CTkLabel(frame, text=label, width=280, anchor='w', font=self.font_input).pack(side='left')
        var = tk.DoubleVar(value=default)
        entry = ctk.CTkEntry(frame, textvariable=var, width=180, font=self.font_input)
        entry.pack(side='left', padx=15)
        return var

    def toggle_auto_trade(self):
        self.auto_trade_enabled = self.auto_trade_switch.get() == 1

        if self.auto_trade_enabled:
            status_text = "自动下单：已开启"
            status_color = "#00ff00"
        else:
            status_text = "自动下单：已关闭（安全模式）"
            status_color = "#ff0000"
            self.send_notification("自动下单已关闭！系统进入安全模式，仅监控不下单。")

        self.auto_trade_status_label.configure(text=status_text, text_color=status_color)

    def send_notification(self, message: str):
        print(f"【通知】: {message}")
        notification_window = ctk.CTkToplevel(self)
        notification_window.title("系统通知")
        notification_window.geometry("400x200")
        ctk.CTkLabel(notification_window, text=message, font=self.font_normal, wraplength=350).pack(pady=50)
        ctk.CTkButton(notification_window, text="确定", command=notification_window.destroy).pack(pady=10)

    def apply_leverage_button(self):
        leverage = int(self.leverage_var.get())
        self.apply_leverage(leverage)

    def apply_leverage(self, leverage):
        try:
            self.trader.set_leverage(self.symbol, leverage)
            self.leverage = leverage
            self.current_leverage_label.configure(text=f"当前杠杆: {leverage}x (已应用)", text_color="#00ff00")
        except Exception as e:
            print(f"杠杆设置失败: {e}")
            self.current_leverage_label.configure(text=f"杠杆设置失败: {e}", text_color="#ff0000")

    def apply_params(self):
        try:
            self.config.setdefault('risk', {})
            self.config['risk']['max_risk_per_trade'] = float(self.risk_var.get()) / 100.0
            self.config['risk']['stop_loss_atr_multiplier'] = float(self.atr_var.get())
            self.config['risk']['take_profit_rr'] = float(self.rr_var.get())

            self.manual_refresh()
        except Exception as e:
            print(f"参数应用失败: {e}")

    def query_balance_pos(self):
        try:
            balance = self.trader.get_balance()
            usdt_bal = self._extract_usdt_balance(balance)
            self.balance_label.configure(text=f"余额: {usdt_bal:.2f} USDT")

            positions = self.trader.get_positions(self.symbol)
            net_pos = 0
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                side = 1 if pos.get('side') == 'long' else -1
                net_pos += contracts * side
            pos_text = "多头" if net_pos > 0 else ("空头" if net_pos < 0 else "空仓")
            self.pos_label.configure(text=f"持仓方向: {pos_text} ({abs(net_pos):.4f} 张)")
        except Exception as e:
            print(f"查询失败: {e}")

    def manual_refresh(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.update_data()

    def _extract_usdt_balance(self, balance):
        try:
            total = balance.get('total', {})
            return float(total.get('USDT', 0))
        except:
            return 0.0

    def update_data(self):
        if not self.winfo_exists():
            return

        try:
            # 获取K线数据（增加limit避免空数据）
            df = self.trader.fetch_latest_ohlcv(self.symbol, self.timeframe, limit=300)
            if df.empty:
                raise ValueError("获取K线数据为空")
            df_enhanced = enhance_dataframe(df, self.config)
            latest = df_enhanced.iloc[-1]
            price = float(latest['close'])
            atr = float(latest.get('atr', 0))

            # 获取实时ticker（当前价格 + 时间）
            realtime_price = price  # 默认备用
            realtime_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            try:
                ticker = self.trader.exchange.fetch_ticker(self.symbol)
                realtime_price = float(ticker['last'])
                realtime_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"实时ticker获取失败，使用K线close作为备用价格: {e}")

            # 余额
            balance = self.trader.get_balance()
            usdt_bal = self._extract_usdt_balance(balance)
            self.balance_label.configure(text=f"余额: {usdt_bal:.2f} USDT")

            signal = int(latest.get('signal', 0))

            # 下单逻辑（保持）
            order_size = float(self.order_size_var.get())
            positions = self.trader.get_positions(self.symbol)
            net_pos = 0
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                side = 1 if pos.get('side') == 'long' else -1
                net_pos += contracts * side

            target_pos = order_size if signal == 1 else (-order_size if signal == -1 else 0)

            if self.auto_trade_enabled and abs(target_pos - net_pos) > 0.0001:
                if net_pos > 0:
                    self.trader.place_order(self.symbol, 'sell', net_pos, order_type='market')
                elif net_pos < 0:
                    self.trader.place_order(self.symbol, 'buy', abs(net_pos), order_type='market')
                if target_pos > 0:
                    self.trader.place_order(self.symbol, 'buy', target_pos, order_type='market')
                elif target_pos < 0:
                    self.trader.place_order(self.symbol, 'sell', abs(target_pos), order_type='market')

            # 更新持仓显示（保持）

            # === 详细信号分析（动态生成，每次不同）===
            analysis_lines = []
            analysis_lines.append(f"【实时信息】")
            analysis_lines.append(f"实时时间 (UTC): {realtime_time}")
            analysis_lines.append(f"实时价格: {realtime_price:.2f} USDT")
            analysis_lines.append(f"最新完成K线起始时间: {latest.name.strftime('%Y-%m-%d %H:%M')} (UTC)")
            analysis_lines.append(f"K线收盘价: {price:.2f}")
            analysis_lines.append("")

            analysis_lines.append(f"【当前信号】: {'强烈买入' if signal == 1 else '强烈卖出' if signal == -1 else '无信号/观望'}")
            analysis_lines.append("")

            if signal != 0:
                direction = "买入（开多/加多）" if signal == 1 else "卖出（开空/加空）"
                analysis_lines.append(f"系统建议: {direction}")
                analysis_lines.append(f"建议下单张数: {order_size:.4f} 张")
                analysis_lines.append("")

            analysis_lines.append(f"【信号生成过程与依据】（多因子动态分析，每次K线不同）")
            analysis_lines.append(f"1. 趋势判断: {'多头趋势（价格 > EMA200）' if price > latest.get('ema_very_long', 0) else '空头或震荡趋势'}")
            analysis_lines.append(f"2. RSI状态: {latest.get('rsi', 0):.1f} ({'超卖区' if latest.get('rsi', 0) < 30 else '超买区' if latest.get('rsi', 0) > 70 else '中性'})")
            analysis_lines.append(f"3. 放量情况: {'是（成交量 > 20期均量1.5倍）' if latest.get('volume', 0) > latest.get('vol_ma20', 0) * 1.5 else '否'}")
            analysis_lines.append(f"4. 量价关系: CMF {'正（资金流入）' if latest.get('cmf', 0) > 0 else '负'} | Volume Osc {'正' if latest.get('volume_osc', 0) > 0 else '负'} | VWAP {'价格在上（支撑）' if price > latest.get('vwap', price) else '价格在下（压力）'}")
            analysis_lines.append("")

            analysis_lines.append(f"【触发因子明细】（本次信号由以下条件组合产生）")
            triggers = []
            candle_triggers = []
            if latest.get('hammer', 0) == 1: candle_triggers.append("锤头线")
            if latest.get('bullish_engulfing', 0) == 1: candle_triggers.append("看涨吞没")
            if latest.get('morning_star', 0) == 1: candle_triggers.append("晨星")
            if latest.get('three_white_soldiers', 0) == 1: candle_triggers.append("三白兵")
            if latest.get('piercing', 0) == 1: candle_triggers.append("穿刺线")
            if candle_triggers:
                triggers.append(f"蜡烛反转形态: {', '.join(candle_triggers)}")

            chart_triggers = []
            if latest.get('double_bottom_confirmed', 0) == 1: chart_triggers.append("双底突破")
            if latest.get('hs_bottom_confirmed', 0) == 1: chart_triggers.append("头肩底突破")
            if latest.get('ascending_triangle', 0) == 1: chart_triggers.append("上升三角")
            if latest.get('bull_flag', 0) == 1: chart_triggers.append("看涨旗形")
            if latest.get('rectangle_break_up', 0) == 1: chart_triggers.append("矩形向上突破")
            if chart_triggers:
                triggers.append(f"图表形态: {', '.join(chart_triggers)}")

            div_triggers = []
            if latest.get('rsi_bullish_div', 0) == 1: div_triggers.append("RSI看涨背离")
            if latest.get('macd_bullish_div', 0) == 1: div_triggers.append("MACD看涨背离")
            if latest.get('obv_bullish_div', 0) == 1: div_triggers.append("OBV看涨背离")
            if div_triggers:
                triggers.append(f"背离信号: {', '.join(div_triggers)}")

            if latest.get('wave_label', 'none') == 'wave_3' and latest.get('wave_confirmed', 0) == 1:
                triggers.append("艾略特第3浪确认")

            if latest.get('trendline_break_up', False):
                triggers.append("趋势线向上突破")

            if triggers:
                for t in triggers:
                    analysis_lines.append(f"  • {t}")
            else:
                analysis_lines.append("  • 本次无特定强因子触发（可能仅基础趋势+量价条件）")

            analysis_lines.append("")
            analysis_lines.append("【总结】本次信号由以上动态因子组合生成，每次K线不同，触发条件不同。")
            analysis_lines.append("策略采用多因子共振，只有多个条件满足才会出强烈信号，避免假突破。")

            self.analysis_text.delete("1.0", "end")
            self.analysis_text.insert("end", "\n".join(analysis_lines))

        except Exception as e:
            print(f"更新错误: {e}")
            traceback.print_exc()
            self.analysis_text.delete("1.0", "end")
            self.analysis_text.insert("end", f"数据加载失败: {e}\n\n正在重试...")

        finally:
            if self.winfo_exists():
                if self.after_id:
                    self.after_cancel(self.after_id)
                interval_sec = max(10, int(self.refresh_interval_var.get()))
                self.after_id = self.after(interval_sec * 1000, self.update_data)

    def on_closing(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        try:
            if hasattr(self.trader, 'close'):
                self.trader.close()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = TradingGUI()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.on_closing()