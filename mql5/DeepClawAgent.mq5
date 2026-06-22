//+------------------------------------------------------------------+
//| DeepClawAgent.mq5                                                |
//| Deep Claw — Unified MQL5 Expert Advisor v1.1                     |
//|                                                                  |
//| Signal chain:                                                    |
//|   ATM Bot trail-flip (exec TF) + MTF Gate + Confidence          |
//|   → Initial entry with ADSA v7 TP1/TP2/Holder management        |
//|   → Pyramid adds on Smart RSI momentum (Claw Protocol style)    |
//|   → Exit ALL on exec trail flip                                  |
//|                                                                  |
//| Scale-in: position open + newSmartBull/Bear fires + count < max |
//|           SL of each add = current exec trail (tightening R)    |
//|                                                                  |
//| Source systems: Claw Protocol + ADSA v7                         |
//| Broker target: Deriv MT5 (standard CTrade/hedge mode)           |
//+------------------------------------------------------------------+
#property copyright "Deep Claw"
#property version   "1.10"
#property description "Deep Claw Agent — ATM Bot + MTF Trail + Confidence + Pyramid"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//=== INPUT PARAMETERS ================================================

input group "=== ATM BOT (exec TF trail-flip) ==="
input int    Inp_ATR_Period    = 1;       // ATR period (Key Factor)
input double Inp_ATR_Mult      = 1.618;   // ATR multiplier

input group "=== MTF LIQUIDITY TRAIL GATE (M5 / M15 / H1) ==="
input bool   Inp_Use_MTF       = true;    // Enable MTF trail gate
input int    Inp_Liq_ATR_Len   = 10;      // Trail ATR period (MTF)
input double Inp_Liq_ATR_Mult  = 1.618;   // Trail ATR multiplier (MTF)
input int    Inp_MTF_Min_Align = 2;       // Min TFs aligned out of 3 to pass gate

input group "=== CONFIDENCE ENGINE ==="
input double Inp_Conf_Thresh   = 60.0;    // Min confidence % to take trade
input double Inp_W_Trail       = 1.5;     // Weight: MTF trail alignment
input double Inp_W_RSI         = 1.0;     // Weight: RSI regime
input double Inp_W_VWAP        = 1.0;     // Weight: VWAP alignment
input double Inp_W_Fib         = 0.5;     // Weight: Fibonacci/trend proxy
input double Inp_W_SMC         = 1.0;     // Weight: SMC structure

input group "=== RSI / SMART MOMENTUM ==="
input int    Inp_RSI_Period    = 14;      // RSI period
input int    Inp_EMA_RSI_Len   = 5;       // EMA period for RSI slope (SmartBull gate)
input int    Inp_RSI_PMom      = 55;      // RSI positive momentum threshold
input int    Inp_RSI_NMom      = 45;      // RSI negative momentum threshold

input group "=== PYRAMID SCALE-INS (Claw Protocol) ==="
input bool   Inp_Enable_Scale  = true;    // Enable pyramid scale-ins
input int    Inp_Max_Scale     = 3;       // Max scale-in adds (1-3)
input double Inp_Scale_Risk    = 0.5;     // Dollar risk per scale-in (% balance)

input group "=== RISK MODEL ==="
input double Inp_Risk_Pct      = 1.0;     // Risk per initial trade (% balance)
input double Inp_SL_ATR_Mult   = 1.5;     // Initial SL = ATR x this
input double Inp_TP1_R         = 1.0;     // TP1 R-multiple
input double Inp_TP2_R         = 2.0;     // TP2 R-multiple
input double Inp_TP3_R         = 3.0;     // TP3 R-multiple
input double Inp_TP1_Frac      = 0.34;    // Fraction to close at TP1
input double Inp_TP2_Frac      = 0.33;    // Fraction of original lots at TP2
input bool   Inp_BE_on_TP2     = true;    // Move SL to breakeven on TP2 hit
input int    Inp_Slippage      = 10;      // Max slippage in points
input ulong  Inp_Magic         = 202401;  // EA magic number

input group "=== JOURNAL ==="
input bool   Inp_Journal       = true;    // Write trade journal CSV

//=== CONSTANTS =======================================================

#define TRAIL_LOOKBACK   300
#define MAX_SCALE        3           // hard ceiling on array sizes
#define JOURNAL_PREFIX   "DeepClaw_"

//=== PHASE ENUM ======================================================

enum ENUM_PHASE {
    PHASE_NONE   = 0,
    PHASE_TP1    = 1,
    PHASE_TP2    = 2,
    PHASE_HOLDER = 3,
};

//=== GLOBAL STATE ====================================================

// ── Exec TF trail ──────────────────────────────────────────────────
double   g_exec_trail      = 0.0;
int      g_exec_trend      = 0;
int      g_prev_exec_trend = 0;

// ── MTF trail cache ────────────────────────────────────────────────
int      g_m5_trend  = 0;
int      g_m15_trend = 0;
int      g_h1_trend  = 0;
datetime g_last_m5   = 0;
datetime g_last_m15  = 0;
datetime g_last_h1   = 0;

// ── RSI / Smart Momentum ───────────────────────────────────────────
double   g_rsi            = 50.0;
bool     g_rsi_bull       = false;
bool     g_rsi_bear       = false;
double   g_ema5_cur       = 0.0;
double   g_ema5_prev      = 0.0;
bool     g_smart_bull     = false;   // current bar: RSI>PMom + EMA5 rising
bool     g_smart_bear     = false;   // current bar: RSI<NMom + EMA5 falling
bool     g_prev_smart_bull = false;  // previous bar state (for edge detection)
bool     g_prev_smart_bear = false;

// ── VWAP / SMC / ATR ──────────────────────────────────────────────
double   g_vwap       = 0.0;
int      g_vwap_swing = 0;
int      g_smc_bias   = 0;
double   g_atr        = 0.0;

// ── Confidence ────────────────────────────────────────────────────
double   g_conf_bull  = 0.0;
double   g_conf_bear  = 0.0;

// ── Position state — only this module writes these ─────────────────
int          g_posState    = 0;
ENUM_PHASE   g_phase       = PHASE_NONE;
double       g_entry       = 0.0;
double       g_sl          = 0.0;      // current SL of initial position
double       g_tp1         = 0.0;
double       g_tp2         = 0.0;
double       g_tp3         = 0.0;
double       g_init_lots   = 0.0;
double       g_sl_dist     = 0.0;     // initial SL distance (for R calc)
ulong        g_ticket      = 0;       // initial position ticket

// ── Pyramid scale-in tracking ──────────────────────────────────────
int          g_scale_count              = 0;
ulong        g_scale_tickets[MAX_SCALE];
double       g_scale_sls[MAX_SCALE];   // SL level when scale-in was added
double       g_scale_lots[MAX_SCALE];

// ── Bar tracking ──────────────────────────────────────────────────
datetime     g_last_bar    = 0;

// ── Indicator handles ─────────────────────────────────────────────
int  g_h_rsi  = INVALID_HANDLE;
int  g_h_atr  = INVALID_HANDLE;
int  g_h_ema5 = INVALID_HANDLE;   // EMA(close,5) for SmartBull slope

// ── Journal ───────────────────────────────────────────────────────
int  g_jfile  = INVALID_HANDLE;

CTrade g_trade;

//=== LIQUIDITY TRAIL =================================================

void CalcLiqTrail(
    const double &C[], const double &H[], const double &L[],
    int atr_len, double atr_mult,
    int &out_trend, double &out_trail
)
{
    int n = ArraySize(C);
    if(n < atr_len + 2) { out_trend = 1; out_trail = (n>0)?C[n-1]:0; return; }

    int    trend = 1;
    double trail = C[0];

    for(int i = 1; i < n; i++)
    {
        double atr_sum = 0.0; int cnt = 0;
        for(int j = i; j > MathMax(0, i-atr_len); j--)
        {
            atr_sum += MathMax(H[j]-L[j], MathMax(MathAbs(H[j]-C[j-1]), MathAbs(L[j]-C[j-1])));
            cnt++;
        }
        double band = (cnt>0) ? (atr_mult * atr_sum / cnt) : 0.0;

        if(trend == 1)
        { double c = MathMax(trail, C[i]-band); if(C[i]<c){trend=-1; trail=C[i]+band;} else trail=c; }
        else
        { double c = MathMin(trail, C[i]+band); if(C[i]>c){trend= 1; trail=C[i]-band;} else trail=c; }
    }
    out_trend = trend; out_trail = trail;
}

int GetTFTrailTrend(ENUM_TIMEFRAMES tf, int atr_len, double atr_mult)
{
    MqlRates rates[]; ArraySetAsSeries(rates, false);
    int n = CopyRates(_Symbol, tf, 0, TRAIL_LOOKBACK, rates);
    if(n < atr_len+2) return 0;
    double C[], H[], L[];
    ArrayResize(C,n); ArrayResize(H,n); ArrayResize(L,n);
    for(int i=0;i<n;i++){C[i]=rates[i].close; H[i]=rates[i].high; L[i]=rates[i].low;}
    int tr; double tv; CalcLiqTrail(C,H,L,atr_len,atr_mult,tr,tv); return tr;
}

void UpdateExecTrail()
{
    MqlRates rates[]; ArraySetAsSeries(rates, false);
    int n = CopyRates(_Symbol, PERIOD_CURRENT, 0, TRAIL_LOOKBACK, rates);
    if(n < Inp_ATR_Period+2) return;
    double C[], H[], L[];
    ArrayResize(C,n); ArrayResize(H,n); ArrayResize(L,n);
    for(int i=0;i<n;i++){C[i]=rates[i].close; H[i]=rates[i].high; L[i]=rates[i].low;}
    g_prev_exec_trend = g_exec_trend;
    CalcLiqTrail(C,H,L,Inp_ATR_Period,Inp_ATR_Mult,g_exec_trend,g_exec_trail);
}

void UpdateMTFTrails()
{
    datetime t[1];
    if(CopyTime(_Symbol,PERIOD_M5,0,1,t)==1 && t[0]!=g_last_m5)
        { g_m5_trend=GetTFTrailTrend(PERIOD_M5,Inp_Liq_ATR_Len,Inp_Liq_ATR_Mult); g_last_m5=t[0]; }
    if(CopyTime(_Symbol,PERIOD_M15,0,1,t)==1 && t[0]!=g_last_m15)
        { g_m15_trend=GetTFTrailTrend(PERIOD_M15,Inp_Liq_ATR_Len,Inp_Liq_ATR_Mult); g_last_m15=t[0]; }
    if(CopyTime(_Symbol,PERIOD_H1,0,1,t)==1 && t[0]!=g_last_h1)
        { g_h1_trend=GetTFTrailTrend(PERIOD_H1,Inp_Liq_ATR_Len,Inp_Liq_ATR_Mult); g_last_h1=t[0]; }
}

//=== MARKET STATE ====================================================

void UpdateRSI()
{
    double buf[2];
    if(CopyBuffer(g_h_rsi,0,1,2,buf)==2)
    {
        g_rsi      = buf[1];  // confirmed bar
        g_rsi_bull = (g_rsi >= Inp_RSI_PMom);
        g_rsi_bear = (g_rsi <= Inp_RSI_NMom);
    }
}

void UpdateATR()
{
    double buf[1];
    if(CopyBuffer(g_h_atr,0,1,1,buf)==1) g_atr = buf[0];
}

void UpdateSmartMomentum()
{
    // SmartBull: RSI > PMom AND EMA5 slope rising (first bar = scale-in trigger)
    // Mirrors Claw Protocol §8: smartBull = rsi>pmom and change_ema5>0
    double buf[2];
    if(CopyBuffer(g_h_ema5,0,1,2,buf)==2)
    {
        g_ema5_cur  = buf[1];   // confirmed bar
        g_ema5_prev = buf[0];   // bar before that

        g_prev_smart_bull = g_smart_bull;
        g_prev_smart_bear = g_smart_bear;

        bool ema5_rising  = g_ema5_cur > g_ema5_prev;
        bool ema5_falling = g_ema5_cur < g_ema5_prev;

        g_smart_bull = (g_rsi > Inp_RSI_PMom) && ema5_rising;
        g_smart_bear = (g_rsi < Inp_RSI_NMom) && ema5_falling;
    }
}

// First bar of SmartBull/Bear state — this is the scale-in trigger
bool IsNewSmartBull() { return  g_smart_bull && !g_prev_smart_bull; }
bool IsNewSmartBear() { return  g_smart_bear && !g_prev_smart_bear; }

void UpdateVWAP()
{
    datetime day_open = iTime(_Symbol,PERIOD_D1,0);
    int bars = Bars(_Symbol,PERIOD_CURRENT,day_open,TimeCurrent());
    if(bars<1) bars=1;
    MqlRates rates[]; ArraySetAsSeries(rates,true);
    int n = CopyRates(_Symbol,PERIOD_CURRENT,0,bars,rates);
    if(n<1){g_vwap=0; g_vwap_swing=0; return;}
    double cv=0,cv2=0;
    for(int i=0;i<n;i++){double tp=(rates[i].high+rates[i].low+rates[i].close)/3; double v=(double)rates[i].tick_volume; cv+=tp*v; cv2+=v;}
    g_vwap = (cv2>0) ? cv/cv2 : iClose(_Symbol,PERIOD_CURRENT,1);
    g_vwap_swing = (iClose(_Symbol,PERIOD_CURRENT,1) > g_vwap) ? 1 : -1;
}

void UpdateSMC()
{
    MqlRates rates[]; ArraySetAsSeries(rates,true);
    int n = CopyRates(_Symbol,PERIOD_CURRENT,1,50,rates);
    if(n<30){g_smc_bias=0; return;}
    double move = rates[0].close - rates[24].close;
    double thr  = g_atr*0.5;
    g_smc_bias  = (move>thr)?1:(move<-thr)?-1:0;
}

//=== CONFIDENCE ENGINE ===============================================

double ComputeConfidence(int direction)
{
    double tw = Inp_W_Trail+Inp_W_RSI+Inp_W_VWAP+Inp_W_Fib+Inp_W_SMC;

    // 1. MTF trail
    double tf = (g_exec_trend==direction)?1.0:0.0;
    if(tf>0){ if(g_m5_trend==direction) tf=MathMin(1.0,tf+0.3); if(g_m15_trend==direction) tf=MathMin(1.0,tf+0.3); if(g_h1_trend==direction) tf=MathMin(1.0,tf+0.2); }

    // 2. RSI
    double rf = (direction==1) ? (g_rsi_bull?1.0:(g_rsi<35?0.5:0.0)) : (g_rsi_bear?1.0:(g_rsi>65?0.5:0.0));

    // 3. VWAP
    double vf = (g_vwap_swing==direction)?1.0:0.0;

    // 4. Fib proxy
    double ff = (vf>0&&g_smc_bias==direction)?1.0:(vf>0||g_smc_bias==direction)?0.5:0.0;

    // 5. SMC
    double sf = (g_smc_bias==direction)?0.8:(g_smc_bias==0)?0.3:0.0;

    return (tw>0) ? ((tf*Inp_W_Trail+rf*Inp_W_RSI+vf*Inp_W_VWAP+ff*Inp_W_Fib+sf*Inp_W_SMC)/tw)*100.0 : 0.0;
}

//=== SIGNAL GENERATOR ================================================

// ATM Bot: exec trail flip on confirmed bar
int GetATMBotSignal()
{
    if(g_prev_exec_trend==0||g_exec_trend==0) return 0;
    if(g_exec_trend==g_prev_exec_trend) return 0;
    double close = iClose(_Symbol,PERIOD_CURRENT,1);
    if(g_exec_trend== 1 && close<=g_exec_trail) return 0;
    if(g_exec_trend==-1 && close>=g_exec_trail) return 0;
    return g_exec_trend;
}

int CountMTFAligned(int dir)
{
    return (int)(g_m5_trend==dir)+(int)(g_m15_trend==dir)+(int)(g_h1_trend==dir);
}

//=== RISK MODEL ======================================================

double ComputeLots(double sl_dist, double risk_pct)
{
    if(sl_dist<=0) return 0;
    double risk_usd  = AccountInfoDouble(ACCOUNT_BALANCE)*(risk_pct/100.0);
    double tick_sz   = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
    double tick_val  = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
    double min_lot   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
    double max_lot   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
    double lot_step  = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
    if(tick_sz<=0||tick_val<=0) return min_lot;
    double usd_per_lot = (sl_dist/tick_sz)*tick_val;
    if(usd_per_lot<=0) return min_lot;
    double lots = MathFloor((risk_usd/usd_per_lot)/lot_step)*lot_step;
    return MathMax(min_lot,MathMin(max_lot,lots));
}

//=== POSITION HELPERS ================================================

bool TicketAlive(ulong ticket)
{
    return (ticket>0 && PositionSelectByTicket(ticket));
}

bool AnyPositionAlive()
{
    if(TicketAlive(g_ticket)) return true;
    for(int i=0;i<g_scale_count;i++) if(TicketAlive(g_scale_tickets[i])) return true;
    return false;
}

bool DoPartialClose(ulong ticket, double frac_of_current)
{
    if(!PositionSelectByTicket(ticket)) return false;
    double lots    = PositionGetDouble(POSITION_VOLUME);
    double lstep   = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
    double minlot  = SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
    double cv      = MathFloor(lots*frac_of_current/lstep)*lstep;
    cv = MathMax(minlot,cv);
    if(cv>=lots) cv=lots;
    return g_trade.PositionClosePartial(ticket,cv,Inp_Slippage);
}

bool DoModifySL(ulong ticket, double new_sl)
{
    if(!PositionSelectByTicket(ticket)) return false;
    double tp = PositionGetDouble(POSITION_TP);
    return g_trade.PositionModify(ticket, new_sl, tp);
}

// Modify SL on initial position AND all alive scale-ins
void ModifyAllSLs(double new_sl)
{
    int digits = (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
    new_sl = NormalizeDouble(new_sl,digits);
    if(TicketAlive(g_ticket) && new_sl!=g_sl)
        { if(DoModifySL(g_ticket,new_sl)) g_sl=new_sl; }
    for(int i=0;i<g_scale_count;i++)
        if(TicketAlive(g_scale_tickets[i]) && new_sl!=g_scale_sls[i])
            { if(DoModifySL(g_scale_tickets[i],new_sl)) g_scale_sls[i]=new_sl; }
}

// Close ALL open positions — fires on trail flip (Claw exit rule)
void CloseAllPositions(string reason)
{
    double exit_px = SymbolInfoDouble(_Symbol,(g_posState==1)?SYMBOL_BID:SYMBOL_ASK);

    if(TicketAlive(g_ticket))
    {
        g_trade.PositionClose(g_ticket,Inp_Slippage);
        double r = (g_posState==1)?(exit_px-g_entry)/g_sl_dist:(g_entry-exit_px)/g_sl_dist;
        WriteJournal(reason,"INITIAL",exit_px,r,g_init_lots);
    }
    for(int i=0;i<g_scale_count;i++)
    {
        if(TicketAlive(g_scale_tickets[i]))
        {
            g_trade.PositionClose(g_scale_tickets[i],Inp_Slippage);
            double sl_d = MathAbs(exit_px - g_scale_sls[i]);
            double r    = (sl_d>0) ? MathAbs(exit_px - g_entry)/sl_d : 0;
            WriteJournal(reason,StringFormat("SCALE_%d",i+1),exit_px,r,g_scale_lots[i]);
        }
    }

    PrintFormat("CloseAll [%s] Reason=%s Scale=%d", (g_posState==1?"LONG":"SHORT"), reason, g_scale_count);
    g_posState   = 0; g_phase=PHASE_NONE;
    g_ticket     = 0; g_scale_count=0;
}

//=== TRADE EXECUTION =================================================

void OpenTrade(int direction)
{
    if(g_atr<=0) return;
    double sl_dist = g_atr * Inp_SL_ATR_Mult;
    double min_stop = SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
    if(sl_dist < min_stop*1.1) sl_dist = min_stop*1.1;

    double lots = ComputeLots(sl_dist, Inp_Risk_Pct);
    if(lots<=0){Print("OpenTrade: invalid lots"); return;}

    double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
    int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
    double entry,sl,tp1,tp2,tp3;

    if(direction==1)
    { entry=ask; sl=NormalizeDouble(entry-sl_dist,digits); tp1=NormalizeDouble(entry+sl_dist*Inp_TP1_R,digits); tp2=NormalizeDouble(entry+sl_dist*Inp_TP2_R,digits); tp3=NormalizeDouble(entry+sl_dist*Inp_TP3_R,digits); }
    else
    { entry=bid; sl=NormalizeDouble(entry+sl_dist,digits); tp1=NormalizeDouble(entry-sl_dist*Inp_TP1_R,digits); tp2=NormalizeDouble(entry-sl_dist*Inp_TP2_R,digits); tp3=NormalizeDouble(entry-sl_dist*Inp_TP3_R,digits); }

    bool ok = (direction==1) ? g_trade.Buy(lots,_Symbol,0,sl,tp3,"DeepClaw") : g_trade.Sell(lots,_Symbol,0,sl,tp3,"DeepClaw");
    if(!ok){PrintFormat("OpenTrade FAILED: %s (%d)",g_trade.ResultRetcodeDescription(),g_trade.ResultRetcode()); return;}

    g_ticket    = g_trade.ResultPosition(); if(g_ticket==0) g_ticket=g_trade.ResultOrder();
    g_posState  = direction; g_phase=PHASE_TP1;
    g_entry     = g_trade.ResultPrice(); g_sl=sl; g_tp1=tp1; g_tp2=tp2; g_tp3=tp3;
    g_init_lots = lots; g_sl_dist=sl_dist; g_scale_count=0;

    PrintFormat("TRADE OPEN [%s] Entry=%.5f SL=%.5f TP1=%.5f TP2=%.5f TP3=%.5f Lots=%.2f Conf=%.1f%%",
        (direction==1?"LONG":"SHORT"), g_entry, sl, tp1, tp2, tp3, lots,
        (direction==1?g_conf_bull:g_conf_bear));
}

// Pyramid add: SL = current exec trail (tighter R as trend progresses)
void DoScaleIn(int direction)
{
    if(!Inp_Enable_Scale) return;
    if(g_scale_count >= MathMin(Inp_Max_Scale, MAX_SCALE)) return;
    if(g_atr<=0) return;

    // SL for this add is the CURRENT trail value
    double sl_price, sl_dist;
    int digits = (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);

    if(direction==1)
    {
        sl_price = NormalizeDouble(g_exec_trail, digits);
        sl_dist  = SymbolInfoDouble(_Symbol,SYMBOL_ASK) - sl_price;
    }
    else
    {
        sl_price = NormalizeDouble(g_exec_trail, digits);
        sl_dist  = sl_price - SymbolInfoDouble(_Symbol,SYMBOL_BID);
    }

    double min_stop = SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
    if(sl_dist <= min_stop*1.1) { Print("ScaleIn: SL too tight vs min stop"); return; }

    double lots = ComputeLots(sl_dist, Inp_Scale_Risk);
    if(lots<=0){ Print("ScaleIn: invalid lots"); return; }

    bool ok = (direction==1)
              ? g_trade.Buy(lots,_Symbol,0,sl_price,0,"DeepClaw-Scale")
              : g_trade.Sell(lots,_Symbol,0,sl_price,0,"DeepClaw-Scale");

    if(!ok){PrintFormat("ScaleIn FAILED: %s (%d)",g_trade.ResultRetcodeDescription(),g_trade.ResultRetcode()); return;}

    int idx = g_scale_count;
    g_scale_tickets[idx] = g_trade.ResultPosition(); if(g_scale_tickets[idx]==0) g_scale_tickets[idx]=g_trade.ResultOrder();
    g_scale_sls[idx]     = sl_price;
    g_scale_lots[idx]    = lots;
    g_scale_count++;

    double entry_px = g_trade.ResultPrice();
    PrintFormat("SCALE-IN #%d [%s] Entry=%.5f SL=%.5f (trail) Lots=%.2f",
        g_scale_count, (direction==1?"LONG":"SHORT"), entry_px, sl_price, lots);
}

//=== POSITION MANAGER ================================================

void RunPositionManager()
{
    if(!AnyPositionAlive())
    {
        // All positions closed by broker (SL or TP)
        double exit_px = iClose(_Symbol,PERIOD_CURRENT,1);
        double r = (g_posState==1)?(exit_px-g_entry)/MathMax(g_sl_dist,1e-9):(g_entry-exit_px)/MathMax(g_sl_dist,1e-9);

        double tol = g_atr*0.3;
        bool at_tp3 = (g_posState==1)?(exit_px>=g_tp3-tol):(exit_px<=g_tp3+tol);
        string reason = at_tp3 ? "TP3" : (g_phase==PHASE_TP1?"SL":(g_phase==PHASE_TP2?"TP1_THEN_SL":"TP2_THEN_SL"));

        WriteJournal(reason,"INITIAL",exit_px,r,g_init_lots);
        PrintFormat("ALL CLOSED [%s] Phase=%d Reason=%s R=%.2f", (g_posState==1?"LONG":"SHORT"),(int)g_phase,reason,r);

        g_posState=0; g_phase=PHASE_NONE; g_ticket=0; g_scale_count=0;
        return;
    }

    double bid = SymbolInfoDouble(_Symbol,SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol,SYMBOL_ASK);
    double cur = (g_posState==1) ? bid : ask;
    int digits = (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);

    // ── Trail-flip exit: Claw Protocol exit rule ───────────────────
    // If exec trail has flipped against our position, close everything
    bool trail_against = (g_posState==1 && g_exec_trend==-1) || (g_posState==-1 && g_exec_trend==1);
    if(trail_against && g_phase==PHASE_TP1)
    {
        // Haven't hit TP1 yet and trail reversed — full exit
        CloseAllPositions("TRAIL_FLIP");
        return;
    }
    // Note: in PHASE_TP2/HOLDER the trail SL is already tight enough to handle this naturally

    // ── TP1 check ─────────────────────────────────────────────────
    if(g_phase==PHASE_TP1)
    {
        bool tp1_hit = (g_posState==1)?(cur>=g_tp1):(cur<=g_tp1);
        if(tp1_hit && TicketAlive(g_ticket))
        {
            if(DoPartialClose(g_ticket, Inp_TP1_Frac))
            {
                g_phase = PHASE_TP2;
                Print("TP1 HIT — partial close ",NormalizeDouble(Inp_TP1_Frac*100,0),"% → Phase:TP2");
            }
        }
    }

    // ── TP2 check ─────────────────────────────────────────────────
    else if(g_phase==PHASE_TP2)
    {
        bool tp2_hit = (g_posState==1)?(cur>=g_tp2):(cur<=g_tp2);
        if(tp2_hit && TicketAlive(g_ticket))
        {
            double frac = Inp_TP2_Frac / MathMax(0.01, 1.0-Inp_TP1_Frac);
            DoPartialClose(g_ticket, frac);

            if(Inp_BE_on_TP2)
            {
                // Breakeven + 0.1 ATR buffer on ALL positions
                double be = (g_posState==1)
                    ? NormalizeDouble(g_entry+g_atr*0.1, digits)
                    : NormalizeDouble(g_entry-g_atr*0.1, digits);
                ModifyAllSLs(be);
            }
            g_phase = PHASE_HOLDER;
            Print("TP2 HIT — SL→BE on all positions  Phase:HOLDER");
        }
    }

    // ── Holder mode: trail ALL SLs with exec trail ─────────────────
    else if(g_phase==PHASE_HOLDER)
    {
        double new_sl;
        if(g_posState==1)
            new_sl = MathMax(g_sl, g_exec_trail);
        else
            new_sl = MathMin(g_sl, g_exec_trail);

        new_sl = NormalizeDouble(new_sl, digits);
        if(new_sl != g_sl) ModifyAllSLs(new_sl);
    }
}

//=== JOURNAL =========================================================

void WriteJournal(string exit_reason, string pos_label, double exit_px, double r, double lots)
{
    if(!Inp_Journal || g_jfile==INVALID_HANDLE) return;
    FileWriteString(g_jfile, StringFormat(
        "%s,%s,%s,%s,%s,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.2f,%.2f\n",
        TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES), _Symbol,
        (g_posState==1?"LONG":"SHORT"), pos_label, exit_reason,
        g_entry, g_sl, g_tp1, g_tp2, g_tp3, exit_px, lots, r));
    FileFlush(g_jfile);
}

//=== DASHBOARD =======================================================

void RenderDashboard()
{
    string ss  = (g_posState== 1)?"LONG" :(g_posState==-1)?"SHORT":"FLAT";
    string ps  = (g_phase==PHASE_TP1)?"TP1 PENDING":(g_phase==PHASE_TP2)?"TP2 PENDING":(g_phase==PHASE_HOLDER)?"HOLDER":"WAITING";
    string m5s = (g_m5_trend== 1)?"↑":(g_m5_trend==-1)?"↓":"?";
    string m15s= (g_m15_trend==1)?"↑":(g_m15_trend==-1)?"↓":"?";
    string h1s = (g_h1_trend== 1)?"↑":(g_h1_trend==-1)?"↓":"?";
    string exs = (g_exec_trend==1)?"↑ BULL":"↓ BEAR";
    string sbs = g_smart_bull?"SMART BULL":(g_smart_bear?"SMART BEAR":"—");
    string nbs = (IsNewSmartBull()||(g_posState==-1&&IsNewSmartBear())) ? " ← PYRAMID NOW" : "";

    Comment(StringFormat(
        "━━━ DEEP CLAW AGENT v1.1 ━━━━━━━━━━━━━━━━━\n"
        "  STATE:    %-8s   PHASE: %s\n"
        "  SCALE-INS: %d / %d\n"
        "━━━ LIQUIDITY TRAIL ━━━━━━━━━━━━━━━━━━━━━━\n"
        "  EXEC:  %-8s  trail=%.5f\n"
        "  M5: %s   M15: %s   H1: %s\n"
        "━━━ SMART MOMENTUM ━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  RSI:   %.1f   EMA5: %.5f  %s\n"
        "  STATE: %s%s\n"
        "━━━ CONFIDENCE ━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ▲BULL: %.0f%%   ▼BEAR: %.0f%%   thresh=%.0f%%\n"
        "  VWAP: %s   SMC: %s\n"
        "━━━ OPEN TRADE ━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  Entry: %.5f   SL: %.5f\n"
        "  TP1:   %.5f   TP2: %.5f\n"
        "  TP3:   %.5f   Lots: %.2f\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ss, ps,
        g_scale_count, MathMin(Inp_Max_Scale,MAX_SCALE),
        exs, g_exec_trail, m5s, m15s, h1s,
        g_rsi, g_ema5_cur,
        (g_rsi>Inp_RSI_PMom?"RSI>PMom":(g_rsi<Inp_RSI_NMom?"RSI<NMom":"mid")),
        sbs, nbs,
        g_conf_bull, g_conf_bear, Inp_Conf_Thresh,
        (g_vwap_swing==1?"ABOVE VWAP":"BELOW VWAP"),
        (g_smc_bias==1?"BULLISH":(g_smc_bias==-1?"BEARISH":"NEUTRAL")),
        g_entry, g_sl, g_tp1, g_tp2, g_tp3, g_init_lots
    ));
}

//=== EA LIFECYCLE ====================================================

int OnInit()
{
    g_trade.SetExpertMagicNumber(Inp_Magic);
    g_trade.SetDeviationInPoints(Inp_Slippage);
    g_trade.SetTypeFilling(ORDER_FILLING_RETURN);

    g_h_rsi  = iRSI(_Symbol, PERIOD_CURRENT, Inp_RSI_Period, PRICE_CLOSE);
    g_h_atr  = iATR(_Symbol, PERIOD_CURRENT, Inp_ATR_Period);
    g_h_ema5 = iMA(_Symbol,  PERIOD_CURRENT, Inp_EMA_RSI_Len, 0, MODE_EMA, PRICE_CLOSE);

    if(g_h_rsi==INVALID_HANDLE||g_h_atr==INVALID_HANDLE||g_h_ema5==INVALID_HANDLE)
    { Print("ERROR: indicator handle creation failed"); return INIT_FAILED; }

    if(Inp_Journal)
    {
        string fname = JOURNAL_PREFIX+_Symbol+"_journal.csv";
        g_jfile = FileOpen(fname,FILE_WRITE|FILE_SHARE_READ|FILE_CSV|FILE_ANSI,',');
        if(g_jfile!=INVALID_HANDLE)
            FileWriteString(g_jfile,"time,symbol,direction,position,exit_reason,entry,sl,tp1,tp2,tp3,exit_price,lots,r_multiple\n");
    }

    // Warm up trails + reset scale arrays
    g_m5_trend  = GetTFTrailTrend(PERIOD_M5,  Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
    g_m15_trend = GetTFTrailTrend(PERIOD_M15, Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
    g_h1_trend  = GetTFTrailTrend(PERIOD_H1,  Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
    datetime t[1];
    if(CopyTime(_Symbol,PERIOD_M5, 0,1,t)==1) g_last_m5 =t[0];
    if(CopyTime(_Symbol,PERIOD_M15,0,1,t)==1) g_last_m15=t[0];
    if(CopyTime(_Symbol,PERIOD_H1, 0,1,t)==1) g_last_h1 =t[0];
    ArrayInitialize(g_scale_tickets,0);
    ArrayInitialize(g_scale_sls,0);
    ArrayInitialize(g_scale_lots,0);

    PrintFormat("Deep Claw Agent INIT — %s  Magic=%u  Conf=%.0f%%  MaxScale=%d",
        _Symbol, Inp_Magic, Inp_Conf_Thresh, Inp_Max_Scale);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    if(g_h_rsi !=INVALID_HANDLE) IndicatorRelease(g_h_rsi);
    if(g_h_atr !=INVALID_HANDLE) IndicatorRelease(g_h_atr);
    if(g_h_ema5!=INVALID_HANDLE) IndicatorRelease(g_h_ema5);
    if(g_jfile !=INVALID_HANDLE) FileClose(g_jfile);
    Comment("");
    PrintFormat("Deep Claw Agent DEINIT — reason=%d", reason);
}

void OnTick()
{
    // ── Every tick: manage open trade ──────────────────────────────
    if(g_posState != 0) RunPositionManager();

    // ── New-bar logic (confirmed candles only) ──────────────────────
    datetime cur_bar = iTime(_Symbol,PERIOD_CURRENT,0);
    if(cur_bar == g_last_bar) { RenderDashboard(); return; }
    g_last_bar = cur_bar;

    // 1. Perception update
    UpdateExecTrail();
    UpdateMTFTrails();
    UpdateRSI();
    UpdateATR();
    UpdateSmartMomentum();   // depends on RSI being updated first
    UpdateVWAP();
    UpdateSMC();

    // 2. Confidence
    g_conf_bull = ComputeConfidence( 1);
    g_conf_bear = ComputeConfidence(-1);

    if(g_posState == 0)
    {
        // ── FLAT: evaluate initial entry ────────────────────────────
        int signal = GetATMBotSignal();
        if(signal != 0)
        {
            bool mtf_ok  = !Inp_Use_MTF || (CountMTFAligned(signal) >= Inp_MTF_Min_Align);
            double conf  = (signal==1)?g_conf_bull:g_conf_bear;
            bool conf_ok = (conf >= Inp_Conf_Thresh);

            if(mtf_ok && conf_ok)
                OpenTrade(signal);
            else
                PrintFormat("Signal BLOCKED [%s] Conf=%.1f%% MTF=%s",
                    (signal==1?"LONG":"SHORT"), conf, (mtf_ok?"OK":"FAIL"));
        }
    }
    else
    {
        // ── IN TRADE: check for pyramid scale-in ────────────────────
        if(Inp_Enable_Scale && g_scale_count < MathMin(Inp_Max_Scale,MAX_SCALE))
        {
            bool scale_trigger = (g_posState== 1 && IsNewSmartBull()) ||
                                 (g_posState==-1 && IsNewSmartBear());
            if(scale_trigger)
            {
                PrintFormat("PYRAMID SIGNAL [%s] SmartMom confirmed — adding scale #%d",
                    (g_posState==1?"LONG":"SHORT"), g_scale_count+1);
                DoScaleIn(g_posState);
            }
        }
    }

    RenderDashboard();
}
