import streamlit as st
import pandas as pd

# -------------------- 规则常量 --------------------
BOM = {
    "P1": {"R1": 1},
    "P2": {"R1": 1, "R2": 1},
    "P3": {"R2": 2, "R3": 1},
    "P4": {"R2": 1, "R3": 1, "R4": 2}
}

STD_DIRECT_COST = {"P1": 2, "P2": 3, "P3": 4, "P4": 5}

LINE_TYPES = {
    "手工生产线": {"cost": 5, "build_time": 1, "prod_cycle": 3, "switch_time": 0, "switch_cost": 0, "salvage": 1},
    "半自动生产线": {"cost": 10, "build_time": 2, "prod_cycle": 2, "switch_time": 1, "switch_cost": 1, "salvage": 2},
    "全自动生产线": {"cost": 15, "build_time": 3, "prod_cycle": 1, "switch_time": 1, "switch_cost": 2, "salvage": 3},
    "柔性生产线": {"cost": 20, "build_time": 4, "prod_cycle": 1, "switch_time": 0, "switch_cost": 0, "salvage": 4}
}

MAT_LEAD_TIME = {"R1": 1, "R2": 1, "R3": 2, "R4": 2}

# -------------------- 1. 状态初始化 --------------------
def init_state():
    if 'init' not in st.session_state:
        st.session_state.year = 1
        st.session_state.quarter = 1
        st.session_state.current_step = 1
        st.session_state.quarter_fees_paid = False
        st.session_state.quarter_production_advanced = False
        
        st.session_state.show_q_summary = False
        st.session_state.last_q_flows = []
        st.session_state.last_q_str = ""
        
        # 初始资产：现金20M，原料3个R1，成品3个P1
        st.session_state.cash = 20
        st.session_state.materials = {"R1": 3, "R2": 0, "R3": 0, "R4": 0}
        st.session_state.products = {"P1": 3, "P2": 0, "P3": 0, "P4": 0}
        
        st.session_state.long_term_loans = [{"amount": 40, "due_year": 6}] 
        st.session_state.short_term_loans = [] 
        st.session_state.usury_loans = []
        st.session_state.tax_payable = 1
        
        st.session_state.factories = [{"id": 1, "type": "大厂房", "status": "自有", "value": 40, "rent": 0}]
        st.session_state.receivables = [{"amount": 15, "arrival_y": 1, "arrival_q": 4}] 
        st.session_state.orders = []
        st.session_state.order_counter = 1
        
        st.session_state.markets = {
            "区域": {"status": "未开发", "progress": 0, "last_invest_y": 0, "req": 1},
            "国内": {"status": "未开发", "progress": 0, "last_invest_y": 0, "req": 2},
            "亚洲": {"status": "未开发", "progress": 0, "last_invest_y": 0, "req": 3},
            "国际": {"status": "未开发", "progress": 0, "last_invest_y": 0, "req": 4}
        }
        st.session_state.isos = {
            "ISO9000": {"status": "未认证", "progress": 0, "last_invest_y": 0, "req": 2},
            "ISO14000": {"status": "未认证", "progress": 0, "last_invest_y": 0, "req": 3}
        }
        st.session_state.rnd = {
            "P1": {"status": "已研发", "progress": 0, "last_invest_q": "", "req": 0, "cost": 0},
            "P2": {"status": "未研发", "progress": 0, "last_invest_q": "", "req": 5, "cost": 1},
            "P3": {"status": "未研发", "progress": 0, "last_invest_q": "", "req": 5, "cost": 2},
            "P4": {"status": "未研发", "progress": 0, "last_invest_q": "", "req": 5, "cost": 3}
        }
        
        # 初始生产线（built_year=0代表以往年份建成，参与维护费和折旧）
        st.session_state.lines = [
            {"id": 1, "type": "手工生产线", "status": "生产中", "product": "P1", "progress": 1, "invested": 3, "last_invest_q": "", "book_value": 5, "built_year": 0},
            {"id": 2, "type": "手工生产线", "status": "生产中", "product": "P1", "progress": 2, "invested": 3, "last_invest_q": "", "book_value": 5, "built_year": 0},
            {"id": 3, "type": "手工生产线", "status": "生产中", "product": "P1", "progress": 3, "invested": 3, "last_invest_q": "", "book_value": 5, "built_year": 0},
            {"id": 4, "type": "半自动生产线", "status": "生产中", "product": "P1", "progress": 1, "invested": 4, "last_invest_q": "", "book_value": 10, "built_year": 0}
        ]
        
        st.session_state.mat_orders = [] 
        st.session_state.log = ["### 方圆ERP初始盘面录入完毕 (现金: 20M, 原料: 3个R1, 成品: 3个P1)"]
        st.session_state.cash_flows = []
        st.session_state.depreciation_log = [] 
        
        st.session_state.current_year_income = {
            "revenue": 0, "direct_cost": 0, "admin": 0, "rent": 0, "mkt_maint": 0, 
            "maint": 0, "ad": 0, "mkt_dev": 0, "iso_dev": 0, "rnd": 0, 
            "switch": 0, "depreciation": 0, "financial": 0, "asset_loss": 0
        }
        
        st.session_state.init = True

init_state()

# -------------------- 2. 核心流转与日志 --------------------
def get_current_q_str():
    return f"Y{st.session_state.year}Q{st.session_state.quarter}"

def log_action(action, cash_delta, detail=""):
    st.session_state.cash += cash_delta
    sign = "+" if cash_delta > 0 else ""
    color = "🟢" if cash_delta > 0 else "🔴" if cash_delta < 0 else "⚪"
    
    log_msg = f"- **[{get_current_q_str()}]** {color} **{action}**: "
    if cash_delta != 0:
        log_msg += f"现金 {sign}{cash_delta}M | "
    log_msg += f"{detail} (余额: {st.session_state.cash}M)"
    
    st.session_state.log.append(log_msg)
    
    toast_icon = "💰" if cash_delta > 0 else "💸" if cash_delta < 0 else "✅"
    st.toast(f"**{action}**\n{detail}", icon=toast_icon)
    
    if cash_delta != 0:
        st.session_state.cash_flows.append({
            "年份": st.session_state.year,
            "季度": st.session_state.quarter,
            "操作科目": action,
            "收支金额(M)": cash_delta,
            "操作明细": detail
        })

def advance_production_lines_for_quarter():
    """每个季度初自动推进产线：满期的完工入库变空闲，未满期的推进1期"""
    if not st.session_state.quarter_production_advanced:
        for line in st.session_state.lines:
            if line['status'] == "生产中":
                cycle = LINE_TYPES[line['type']]['prod_cycle']
                if line['progress'] >= cycle:
                    line['status'], line['progress'] = "空闲", 0
                    st.session_state.products[line['product']] += 1
                    log_action("生产下线入库", 0, f"L{line['id']}({line['type']}) 完工 {line['product']} 下线入库 (成品库: {st.session_state.products[line['product']]})")
                else:
                    line['progress'] += 1
            elif line['status'] == "转产中":
                line['status'] = "空闲"
        st.session_state.quarter_production_advanced = True

def check_bom(product):
    for mat, qty in BOM[product].items():
        if st.session_state.materials.get(mat, 0) < qty:
            return False, f"原料 {mat} 不足 (现有 {st.session_state.materials.get(mat, 0)}，需 {qty})"
    return True, "充足"

def consume_bom(product):
    for mat, qty in BOM[product].items():
        st.session_state.materials[mat] -= qty

def next_step():
    st.toast("已进入下一步！", icon="➡️")
    st.session_state.current_step += 1

def prev_step():
    st.toast("已返回上一步！", icon="⬅️")
    st.session_state.current_step -= 1

# -------------------- 3. 侧边栏：大盘监控 --------------------
with st.sidebar:
    st.header("🏢 方圆ERP沙盘监控")
    st.metric(label=f"当前进度: {get_current_q_str()}", value=f"现金: {st.session_state.cash} M")
    st.progress(st.session_state.current_step / 5.0, text=f"本季操作进度: {st.session_state.current_step}/5")
    
    with st.expander("📦 原料与成品全量库存", expanded=True):
        st.markdown("**原材料存量：**")
        m_cols = st.columns(4)
        for idx, (m_k, m_v) in enumerate(st.session_state.materials.items()):
            m_cols[idx].metric(label=m_k, value=m_v)
            
        st.markdown("**成品库存量：**")
        p_cols = st.columns(4)
        for idx, (p_k, p_v) in enumerate(st.session_state.products.items()):
            p_cols[idx].metric(label=p_k, value=p_v)

    with st.expander("🚨 紧急融资 (高利贷)", expanded=False):
        st.warning("随时可办理，20%利息，次年同季归还本息")
        usury_amt = st.number_input("申请高利贷(M)", min_value=0, step=20)
        if st.button("立即借入高利贷"):
            if usury_amt > 0:
                st.session_state.usury_loans.append({"amount": usury_amt, "due_y": st.session_state.year + 1, "due_q": st.session_state.quarter})
                log_action("借入高利贷", usury_amt, f"次年Q{st.session_state.quarter}到期归还")
                st.rerun()

    with st.expander("💸 负债与税务", expanded=False):
        st.write(f"- 短贷: {sum(l['amount'] for l in st.session_state.short_term_loans)}M")
        st.write(f"- 长贷: {sum(l['amount'] for l in st.session_state.long_term_loans)}M")
        st.write(f"- 高利贷: {sum(l['amount'] for l in st.session_state.usury_loans)}M")
        st.write(f"- **应交税金: {st.session_state.tax_payable}M**")

    with st.expander("📝 应收账款明细", expanded=False):
        if st.session_state.receivables:
            for r in st.session_state.receivables:
                st.write(f"- {r['amount']}M (预计 Y{r['arrival_y']}Q{r['arrival_q']} 到账)")
        else:
            st.write("无应收款")
        
    with st.expander("⚙️ 生产线状态与现值", expanded=True):
        for line in st.session_state.lines:
            cycle = LINE_TYPES[line['type']]['prod_cycle']
            if line['status'] == "空闲": 
                st.write(f"✅ **L{line['id']}** ({line['type']}): 空闲 | 现值: {line['book_value']}M")
            elif line['status'] == "生产中": 
                st.write(f"⚙️ **L{line['id']}** ({line['type']}): 产{line['product']} ({line['progress']}/{cycle}期) | 现值: {line['book_value']}M")
            elif line['status'] == "转产中": 
                st.write(f"🔄 **L{line['id']}** ({line['type']}): 转产中 | 现值: {line['book_value']}M")
            elif line['status'] == "建设中": 
                b_time = LINE_TYPES[line['type']]['build_time']
                st.write(f"🚧 **L{line['id']}** ({line['type']}): 建设中({line['progress']}/{b_time})")

# -------------------- 4. 主面板交互 --------------------
st.title("方圆 ERP 沙盘自动化推演系统")
tab_ops, tab_reports, tab_log = st.tabs(["▶️ 当前季度操作向导", "📊 财务报表", "📜 日志存档"])

with tab_ops:
    if st.session_state.show_q_summary:
        st.success(f"### 📊 {st.session_state.last_q_str} 现金流与经营报告")
        if st.session_state.last_q_flows:
            st.dataframe(pd.DataFrame(st.session_state.last_q_flows), use_container_width=True, hide_index=True)
            q_in = sum(f['收支金额(M)'] for f in st.session_state.last_q_flows if f['收支金额(M)'] > 0)
            q_out = sum(f['收支金额(M)'] for f in st.session_state.last_q_flows if f['收支金额(M)'] < 0)
            st.write(f"**上季净现金流：** {q_in + q_out}M (收入 {q_in}M，支出 {q_out}M)")
        else:
            st.info("该季度无现金流水记录。")
            
        if "Q4" in st.session_state.last_q_str:
            st.divider()
            st.markdown("### 📋 方圆ERP 年末资产负债与权益快报")
            cash_tot = st.session_state.cash
            ar_tot = sum(r['amount'] for r in st.session_state.receivables)
            mat_tot = sum(st.session_state.materials.values()) * 1
            
            wip_lines = [l for l in st.session_state.lines if l['status'] == '生产中']
            wip_tot = sum(STD_DIRECT_COST[l['product']] for l in wip_lines)
            prod_tot = sum(v * STD_DIRECT_COST[k] for k, v in st.session_state.products.items())
            total_current_assets = cash_tot + ar_tot + mat_tot + wip_tot + prod_tot
            
            fac_tot = sum(f['value'] for f in st.session_state.factories if f['status'] == '自有')
            line_net_tot = sum(l['book_value'] for l in st.session_state.lines)
            total_fixed_assets = fac_tot + line_net_tot
            total_assets = total_current_assets + total_fixed_assets
            
            st_liab = sum(l['amount'] for l in st.session_state.short_term_loans)
            lt_liab = sum(l['amount'] for l in st.session_state.long_term_loans)
            usury_liab = sum(l['amount'] for l in st.session_state.usury_loans)
            tax_liab = st.session_state.tax_payable
            total_liabilities = st_liab + lt_liab + usury_liab + tax_liab
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown("##### 🟢 资产情况 (Assets)")
                st.write(f"- **流动资产合计:** {total_current_assets}M")
                st.write(f"  - 现金: {cash_tot}M | 应收账款: {ar_tot}M")
                st.write(f"  - 原料价值: {mat_tot}M | 在制品价值: {wip_tot}M | 成品价值: {prod_tot}M")
                st.write(f"- **固定资产合计:** {total_fixed_assets}M")
                st.markdown(f"**资产总计 (Total Assets): {total_assets} M**")
                
            with col_b2:
                st.markdown("##### 🔴 负债情况 (Liabilities)")
                st.write(f"- **流动负债:** {st_liab + usury_liab + tax_liab}M")
                st.write(f"- **长期负债:** {lt_liab}M")
                st.markdown(f"**负债总计 (Total Liabilities): {total_liabilities} M**")
                st.markdown(f"**所有者权益: {total_assets - total_liabilities} M**")

        if st.button("知道了，关闭报告进入下一季", type="primary"):
            st.session_state.show_q_summary = False
            st.rerun()
        st.divider()
        st.stop()

    st.subheader(f"📅 第 {st.session_state.year} 年 第 {st.session_state.quarter} 季度")
    
    # ================= 步骤 1 =================
    with st.expander("📍 步骤 1: 财务操作 (季初产线推进、自动结算与贷款)", expanded=(st.session_state.current_step == 1)):
        if st.session_state.current_step == 1:
            
            if not st.session_state.quarter_production_advanced:
                advance_production_lines_for_quarter()
                st.rerun()
            
            st.markdown("#### A. 应收账款贴现")
            if st.session_state.receivables:
                r_options = [f"Y{r['arrival_y']}Q{r['arrival_q']} - {r['amount']}M (ID:{i})" for i, r in enumerate(st.session_state.receivables)]
                r_sel = st.selectbox("选择应收账款贴现 (每7M贴现得6M现金)", range(len(r_options)), format_func=lambda x: r_options[x])
                sel_ar = st.session_state.receivables[r_sel]
                max_discount = (sel_ar['amount'] // 7) * 7
                if max_discount > 0:
                    disc_amt = st.number_input("贴现金额 (必须是7的倍数)", min_value=7, max_value=max_discount, step=7)
                    if st.button(f"执行贴现 (提取{disc_amt}M)"):
                        fee = disc_amt // 7
                        cash_got = disc_amt - fee
                        sel_ar['amount'] -= disc_amt
                        if sel_ar['amount'] == 0:
                            st.session_state.receivables.pop(r_sel)
                        log_action("应收账款贴现", cash_got, f"贴现{disc_amt}M，扣除贴息{fee}M")
                        st.session_state.current_year_income["financial"] += fee
                        st.rerun()
                else:
                    st.info("该账款金额不足7M，无法贴现。")
            else:
                st.write("暂无应收账款可供贴现。")

            st.divider()
            st.markdown("#### B. 自动费用结算与年末折旧")
            rent_fee = sum(f['rent'] for f in st.session_state.factories if f['status'] == '租赁')
            dev_mkt = [m for m, d in st.session_state.markets.items() if d['status'] == "已开发"]
            
            total_auto_deduct = 1
            summary = ["- 扣除本季行政管理费: 1M"]
            
            if st.session_state.quarter == 1:
                if rent_fee > 0:
                    summary.append(f"- 支付全年厂房租金: {rent_fee}M")
                    total_auto_deduct += rent_fee
                if st.session_state.tax_payable > 0:
                    summary.append(f"- 缴纳上年应交税金: {st.session_state.tax_payable}M")
                    total_auto_deduct += st.session_state.tax_payable
                if dev_mkt:
                    summary.append(f"- 支付已开发市场维护费: {len(dev_mkt)}M ({','.join(dev_mkt)})")
                    total_auto_deduct += len(dev_mkt)
                    
            if st.session_state.quarter == 4:
                lt_interest = int(sum(l['amount'] for l in st.session_state.long_term_loans) * 0.1)
                # 规则更新：仅对当年之前建成的旧生产线收取维护费，当年生产/建成的生产线免收维护费
                maint_lines = [l for l in st.session_state.lines if l['status'] != "建设中" and l['built_year'] < st.session_state.year]
                line_maint_fee = len(maint_lines)
                
                if lt_interest > 0:
                    summary.append(f"- 支付长贷利息 (10%): {lt_interest}M")
                    total_auto_deduct += lt_interest
                if line_maint_fee > 0:
                    summary.append(f"- 支付设备维护费 (往年建成设备免新产线): {line_maint_fee}M")
                    total_auto_deduct += line_maint_fee
                else:
                    summary.append("- 设备维护费: 0M (无往年建成的计提设备)")
                    
                summary.append("- 📉 **年末自动计提折旧 (余额递减法)**")
                
            st.markdown("\n".join(summary))
            
            if not st.session_state.quarter_fees_paid:
                if st.button(f"🚀 确认并支付本季各项费用 (共需现金 {total_auto_deduct}M)", type="primary"):
                    if st.session_state.cash >= total_auto_deduct:
                        log_action("自动扣款", -1, "扣除行政管理费")
                        st.session_state.current_year_income["admin"] += 1
                        
                        if st.session_state.quarter == 1:
                            if rent_fee > 0: 
                                log_action("自动扣款", -rent_fee, "支付租赁厂房租金")
                                st.session_state.current_year_income["rent"] += rent_fee
                            if st.session_state.tax_payable > 0:
                                log_action("自动扣款", -st.session_state.tax_payable, "缴纳所得税")
                                st.session_state.tax_payable = 0
                            if dev_mkt: 
                                log_action("自动扣款", -len(dev_mkt), f"支付市场维护费")
                                st.session_state.current_year_income["mkt_maint"] += len(dev_mkt)
                                
                        if st.session_state.quarter == 4:
                            if lt_interest > 0: 
                                log_action("自动扣款", -lt_interest, "支付长贷利息")
                                st.session_state.current_year_income["financial"] += lt_interest
                            
                            # 扣除符合条件的维护费（当年建成的线不收维护费）
                            maint_lines = [l for l in st.session_state.lines if l['status'] != "建设中" and l['built_year'] < st.session_state.year]
                            line_maint_fee = len(maint_lines)
                            if line_maint_fee > 0: 
                                log_action("自动扣款", -line_maint_fee, f"支付老设备维护费共 {line_maint_fee}M")
                                st.session_state.current_year_income["maint"] += line_maint_fee
                            
                            # 折旧：建成下一年起计提
                            total_dep = 0
                            for line in st.session_state.lines:
                                if line['status'] != "建设中" and line['built_year'] < st.session_state.year:
                                    salvage = LINE_TYPES[line['type']]['salvage']
                                    if line['book_value'] > salvage:
                                        dep = line['book_value'] // 3 if line['book_value'] >= 3 else 1
                                        actual_dep = min(dep, line['book_value'] - salvage)
                                        line['book_value'] -= actual_dep
                                        total_dep += actual_dep
                                        st.session_state.depreciation_log.append({"year": st.session_state.year, "line": line['id'], "amount": actual_dep})
                            if total_dep > 0:
                                log_action("计提折旧", 0, f"本年计提折旧共 {total_dep}M")
                                st.session_state.current_year_income["depreciation"] += total_dep
                        
                        st.session_state.quarter_fees_paid = True
                        st.rerun()
                    else:
                        st.error(f"❌ 现金不足！需 {total_auto_deduct}M，当前仅 {st.session_state.cash}M。")
            else:
                st.success("✅ 本季日常费用已结清。")

            st.divider()
            st.markdown("#### C. 贷款管理 (更新及还款)")
            due_st = [l for l in st.session_state.short_term_loans if l['due_y'] == st.session_state.year and l['due_q'] == st.session_state.quarter]
            due_lt = [l for l in st.session_state.long_term_loans if l['due_year'] == st.session_state.year]
            due_usury = [l for l in st.session_state.usury_loans if l['due_y'] == st.session_state.year and l['due_q'] == st.session_state.quarter]
            has_dues = bool(due_st or due_lt or due_usury)

            col_l1, col_l2 = st.columns(2)
            with col_l1:
                st.write("**短贷 (5%利息，次年同季到期)**")
                st_amt = st.number_input("申请短贷(M)", min_value=0, step=20)
                if st.button("借入短贷"):
                    st.session_state.short_term_loans.append({"amount": st_amt, "due_y": st.session_state.year + 1, "due_q": st.session_state.quarter})
                    log_action("借入短贷", st_amt, "次年同季到期")
                    st.rerun()
                
                if due_st:
                    t_prin = sum(l['amount'] for l in due_st)
                    t_int = sum(int(l['amount']*0.05) for l in due_st)
                    if st.button(f"归还到期短贷本息 ({t_prin + t_int}M)"):
                        if st.session_state.cash >= (t_prin + t_int):
                            log_action("归还短贷", -(t_prin + t_int), "归还短贷本息")
                            st.session_state.current_year_income["financial"] += t_int
                            st.session_state.short_term_loans = [l for l in st.session_state.short_term_loans if l not in due_st]
                            st.rerun()
                        else: st.error("❌ 现金不足！")

                if due_usury:
                    u_prin = sum(l['amount'] for l in due_usury)
                    u_int = sum(int(l['amount']*0.20) for l in due_usury)
                    if st.button(f"归还到期高利贷本息 ({u_prin + u_int}M)"):
                        if st.session_state.cash >= (u_prin + u_int):
                            log_action("归还高利贷", -(u_prin + u_int), "归还高利贷本息")
                            st.session_state.current_year_income["financial"] += u_int
                            st.session_state.usury_loans = [l for l in st.session_state.usury_loans if l not in due_usury]
                            st.rerun()
                        else: st.error("❌ 现金不足！")

            with col_l2:
                st.write("**长贷 (10%利息，5年后到期)**")
                if st.session_state.quarter == 4:
                    lt_amt = st.number_input("申请长贷(M)", min_value=0, step=20)
                    if st.button("借入长贷"):
                        st.session_state.long_term_loans.append({"amount": lt_amt, "due_year": st.session_state.year + 5})
                        log_action("借入长贷", lt_amt, f"Y{st.session_state.year+5}年底到期")
                        st.rerun()
                else:
                    st.info("长贷需在每年第四季度办理。")
                    
                if due_lt:
                    t_lt = sum(l['amount'] for l in due_lt)
                    if st.button(f"归还到期长贷本金 ({t_lt}M)"):
                        if st.session_state.cash >= t_lt:
                            log_action("归还长贷", -t_lt, "归还长贷本金")
                            st.session_state.long_term_loans = [l for l in st.session_state.long_term_loans if l not in due_lt]
                            st.rerun()
                        else: st.error("❌ 现金不足！")

            st.divider()
            if has_dues:
                st.error("🚨 警告：本季度有到期贷款必须归还后才能进入下一步！")
            elif not st.session_state.quarter_fees_paid:
                st.warning("⚠️ 请先确认支付本季常规费用。")
            else:
                if st.button("完成财务操作，进入订单环节 ⏭️", type="primary", use_container_width=True):
                    next_step()
                    st.rerun()
        elif st.session_state.current_step > 1:
            st.success("本步骤已完成。")

    # ================= 步骤 2 =================
    with st.expander("📍 步骤 2: 广告投入与订单管理", expanded=(st.session_state.current_step == 2)):
        if st.session_state.current_step == 2:
            st.markdown("#### A. 市场广告投入")
            ad_amt = st.number_input("本年广告总投入(M)", min_value=1, value=1)
            if st.button(f"支付广告费 {ad_amt}M"):
                if st.session_state.cash >= ad_amt:
                    log_action("支付广告费", -ad_amt, "投入市场广告")
                    st.session_state.current_year_income["ad"] += ad_amt
                    st.rerun()
                else:
                    st.error("❌ 现金不足以支付该笔广告费！")
            
            st.divider()
            st.markdown("#### B. 订单登记与交货")
            available_prods = [p for p, d in st.session_state.rnd.items() if d['status'] == "已研发"]
            if not available_prods: available_prods = ["P1"]
            
            c_prod, c_qty, c_rev, c_term, c_btn = st.columns([2, 1, 1, 1, 1])
            with c_prod: o_prod = st.selectbox("录入订单", available_prods)
            with c_qty: o_qty = st.number_input("数量", min_value=1, value=1)
            with c_rev: o_rev = st.number_input("总金额", min_value=1, value=5)
            with c_term: o_term = st.number_input("账期(Q)", min_value=0, max_value=4, value=2)
            with c_btn:
                st.write("")
                st.write("")
                if st.button("登记单据"):
                    st.session_state.orders.append({"id": st.session_state.order_counter, "product": o_prod, "qty": o_qty, "revenue": o_rev, "terms": o_term})
                    log_action("登记订单", 0, f"单号{st.session_state.order_counter}: {o_prod} x{o_qty}")
                    st.session_state.order_counter += 1
                    st.rerun()
                    
            if st.session_state.orders:
                st.divider()
                for o in st.session_state.orders:
                    cc1, cc2, cc3 = st.columns([3, 1, 2])
                    cc1.write(f"待交货: {o['product']} x{o['qty']} (收入 {o['revenue']}M, {o['terms']}期)")
                    stock = st.session_state.products[o['product']]
                    cc2.write(f"当前库存: **{stock}**")
                    if stock >= o['qty']:
                        if cc3.button("执行交货", key=f"deliv_{o['id']}"):
                            st.session_state.products[o['product']] -= o['qty']
                            st.session_state.current_year_income["revenue"] += o['revenue']
                            st.session_state.current_year_income["direct_cost"] += (STD_DIRECT_COST[o['product']] * o['qty'])
                            
                            arr_q = st.session_state.quarter + o['terms']
                            arr_y = st.session_state.year + (arr_q - 1) // 4
                            arr_q = (arr_q - 1) % 4 + 1
                            if o['terms'] == 0: 
                                log_action("现金交货", o['revenue'], f"交出 {o['qty']}个{o['product']} (库余: {st.session_state.products[o['product']]})")
                            else:
                                st.session_state.receivables.append({"amount": o['revenue'], "arrival_q": arr_q, "arrival_y": arr_y})
                                log_action("账期交货", 0, f"交出 {o['qty']}个{o['product']}，增应收 {o['revenue']}M (库余: {st.session_state.products[o['product']]})")
                            st.session_state.orders = [order for order in st.session_state.orders if order['id'] != o['id']]
                            st.rerun()
                    else: cc3.error("库存不足")
            
            st.divider()
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("⬅️ 返回财务环节"):
                    prev_step()
                    st.rerun()
            with cb2:
                if st.button("完成/跳过订单环节 ⏭️", type="primary"):
                    next_step()
                    st.rerun()
        elif st.session_state.current_step > 2:
            st.success("本步骤已完成。")

    # ================= 步骤 3 =================
    with st.expander("📍 步骤 3: 生产线投料与转产", expanded=(st.session_state.current_step == 3)):
        if st.session_state.current_step == 3:
            st.info("💡 空闲产线投料后立即开始本季生产（进度置为第1期），消耗对应原料与 1M 加工费。")
            available_prods = [p for p, d in st.session_state.rnd.items() if d['status'] == "已研发"]
            
            for line in st.session_state.lines:
                if line['status'] == "空闲":
                    cols = st.columns([2, 1, 1, 2])
                    cols[0].write(f"**L{line['id']}** ({line['type']})")
                    cols[1].write(f"配置: **{line['product']}**")
                    target_prod = cols[2].selectbox("选择产品", available_prods, key=f"sel_{line['id']}")
                    
                    switch_time = LINE_TYPES[line['type']]['switch_time']
                    switch_cost = LINE_TYPES[line['type']]['switch_cost']
                    
                    if target_prod == line['product']:
                        if cols[3].button("投料上线 (耗料+1M)", key=f"btn_{line['id']}"):
                            can_prod, msg = check_bom(target_prod)
                            if can_prod:
                                if st.session_state.cash >= 1:
                                    consume_bom(target_prod)
                                    line['status'], line['progress'] = "生产中", 1
                                    log_action("上线投料加工", -1, f"L{line['id']} 投入生产 {target_prod}")
                                    st.rerun()
                                else: st.error("❌ 现金不足支付 1M 加工费！")
                            else: st.error(msg)
                    else:
                        if cols[3].button(f"转产至{target_prod} ({switch_cost}M)", key=f"btn_{line['id']}"):
                            if st.session_state.cash >= switch_cost:
                                line['product'] = target_prod
                                line['status'] = "转产中" if switch_time > 0 else "空闲"
                                log_action("生产线转产", -switch_cost, f"L{line['id']} 转产至 {target_prod}")
                                st.session_state.current_year_income["switch"] += switch_cost
                                st.rerun()
                            else: st.error("❌ 现金不足支付转产费！")
            
            st.divider()
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("⬅️ 返回订单环节"):
                    prev_step()
                    st.rerun()
            with cb2:
                if st.button("完成/跳过生产环节 ⏭️", type="primary"):
                    next_step()
                    st.rerun()
        elif st.session_state.current_step > 3:
            st.success("本步骤已完成。")

    # ================= 步骤 4 =================
    with st.expander("📍 步骤 4: 资产处置、投资、研发、外部交易与采购", expanded=(st.session_state.current_step == 4)):
        if st.session_state.current_step == 4:
            
            st.markdown("##### 1. 原材料采购")
            c1, c2, c3 = st.columns(3)
            with c1: mat_choice = st.selectbox("选择原料", ["R1", "R2", "R3", "R4"])
            with c2: mat_qty = st.number_input("采购数量", min_value=1, value=1)
            with c3:
                st.write("")
                st.write("")
                if st.button("下达采购单"):
                    arr_q = st.session_state.quarter + MAT_LEAD_TIME[mat_choice]
                    arr_y = st.session_state.year + (arr_q - 1) // 4
                    arr_q = (arr_q - 1) % 4 + 1
                    st.session_state.mat_orders.append({"mat": mat_choice, "qty": mat_qty, "arrival_q": arr_q, "arrival_y": arr_y})
                    log_action("下达原料订单", 0, f"订购 {mat_qty}个{mat_choice}，预计 Y{arr_y}Q{arr_q} 抵达")
            
            st.divider()
            st.markdown("##### 2. 外部企业交易 (即时现款交割)")
            col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([1, 1, 1, 1, 1])
            with col_t1: t_action = st.selectbox("类型", ["买入", "卖出"])
            with col_t2: t_item = st.selectbox("物品", ["R1", "R2", "R3", "R4", "P1", "P2", "P3", "P4"])
            with col_t3: t_qty = st.number_input("数量", min_value=1, value=1, key="t_q")
            with col_t4: t_price = st.number_input("总金额(M)", min_value=0, value=1, key="t_p")
            with col_t5:
                st.write("")
                st.write("")
                if st.button("确认交易"):
                    if t_action == "买入":
                        if st.session_state.cash >= t_price:
                            if t_item.startswith("R"): st.session_state.materials[t_item] += t_qty
                            else: st.session_state.products[t_item] += t_qty
                            log_action("外部买入", -t_price, f"购入 {t_qty}个{t_item}，已直接入库")
                            st.rerun()
                        else: st.error("❌ 现金不足！")
                    else:
                        stock_ok = False
                        if t_item.startswith("R") and st.session_state.materials[t_item] >= t_qty:
                            st.session_state.materials[t_item] -= t_qty
                            stock_ok = True
                        elif t_item.startswith("P") and st.session_state.products[t_item] >= t_qty:
                            st.session_state.products[t_item] -= t_qty
                            stock_ok = True
                        
                        if stock_ok:
                            log_action("外部卖出", t_price, f"售出 {t_qty}个{t_item}，已直接扣减库存")
                            st.rerun()
                        else: st.error("❌ 库存不足！")

            st.divider()
            st.markdown("##### 3. 资产处置 (出售厂房与生产线)")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                owned_facs = [f for f in st.session_state.factories if f['status'] == '自有']
                if owned_facs:
                    sell_fac_id = st.selectbox("出售厂房 (换取次年同季应收账款)", [f['id'] for f in owned_facs], format_func=lambda x: next(f['type'] for f in owned_facs if f['id'] == x))
                    target_fac = next(f for f in owned_facs if f['id'] == sell_fac_id)
                    if st.button(f"出售 {target_fac['type']} ({target_fac['value']}M)"):
                        st.session_state.factories = [f for f in st.session_state.factories if f['id'] != sell_fac_id]
                        st.session_state.receivables.append({"amount": target_fac['value'], "arrival_q": st.session_state.quarter, "arrival_y": st.session_state.year + 1})
                        log_action("出售厂房", 0, f"出售{target_fac['type']}，获得4期应收款")
                        st.rerun()
                else:
                    st.write("目前无自有厂房可出售。")
            with col_s2:
                if st.session_state.lines:
                    sell_line_id = st.selectbox("出售生产线 (立即得残值现金)", [l['id'] for l in st.session_state.lines], format_func=lambda x: next(f"L{l['id']} - {l['type']} (净值{l['book_value']}M)" for l in st.session_state.lines if l['id'] == x))
                    target_line = next(l for l in st.session_state.lines if l['id'] == sell_line_id)
                    salvage_val = LINE_TYPES[target_line['type']]['salvage']
                    loss = max(0, target_line['book_value'] - salvage_val)
                    if st.button(f"按残值 {salvage_val}M 出售 L{sell_line_id}"):
                        st.session_state.lines = [l for l in st.session_state.lines if l['id'] != sell_line_id]
                        st.session_state.current_year_income["asset_loss"] += loss
                        log_action("出售生产线", salvage_val, f"出售 L{sell_line_id}，资产损失 {loss}M")
                        st.rerun()
                else:
                    st.write("目前无生产线可出售。")

            st.divider()
            st.markdown("##### 4. 厂房购买与租赁 (上限: 1大1小)")
            has_big = any(f['type'] == '大厂房' for f in st.session_state.factories)
            has_small = any(f['type'] == '小厂房' for f in st.session_state.factories)
            
            fac_buy_options = []
            if not has_big: fac_buy_options.append("大厂房 (40M)")
            if not has_small: fac_buy_options.append("小厂房 (30M)")
            
            fac_rent_options = []
            if not has_big: fac_rent_options.append("大厂房 (5M/年)")
            if not has_small: fac_rent_options.append("小厂房 (3M/年)")

            cf1, cf2 = st.columns(2)
            with cf1:
                if fac_buy_options:
                    fac_buy_type = st.selectbox("购买厂房", fac_buy_options)
                    buy_cost = 40 if "大" in fac_buy_type else 30
                    if st.button(f"全款购买 ({buy_cost}M)"):
                        if st.session_state.cash >= buy_cost:
                            new_id = (max([f['id'] for f in st.session_state.factories]) + 1) if st.session_state.factories else 1
                            fac_t = "大厂房" if "大" in fac_buy_type else "小厂房"
                            st.session_state.factories.append({"id": new_id, "type": fac_t, "status": "自有", "value": buy_cost, "rent": 0})
                            log_action("购买厂房", -buy_cost, f"购入{fac_t}")
                            st.rerun()
                        else: st.error("❌ 现金不足！")
                else: st.success("已达到厂房持有上限。")
            with cf2:
                if fac_rent_options:
                    fac_rent_type = st.selectbox("租赁厂房", fac_rent_options)
                    rent_cost = 5 if "大" in fac_rent_type else 3
                    if st.button(f"立即租赁并付当年租金 ({rent_cost}M)"):
                        if st.session_state.cash >= rent_cost:
                            new_id = (max([f['id'] for f in st.session_state.factories]) + 1) if st.session_state.factories else 1
                            fac_t = "大厂房" if "大" in fac_rent_type else "小厂房"
                            st.session_state.factories.append({"id": new_id, "type": fac_t, "status": "租赁", "value": 0, "rent": rent_cost})
                            log_action("租赁厂房", -rent_cost, f"租用{fac_t}")
                            st.session_state.current_year_income["rent"] += rent_cost
                            st.rerun()
                        else: st.error("❌ 现金不足！")
                else: st.success("已达到厂房持有上限。")
            
            st.divider()
            st.markdown("##### 5. 市场开拓与资格认证 (每年第四季度)")
            if st.session_state.quarter == 4:
                col_mkt, col_iso = st.columns(2)
                with col_mkt:
                    for m, d in st.session_state.markets.items():
                        if d['status'] != "已开发" and d['last_invest_y'] != st.session_state.year:
                            if st.button(f"开拓 {m} 市场 (1M) - {d['progress']}/{d['req']}", key=f"m_{m}"):
                                if st.session_state.cash >= 1:
                                    d['progress'] += 1
                                    d['last_invest_y'] = st.session_state.year
                                    log_action("市场开发", -1, f"开拓 {m} ({d['progress']}/{d['req']})")
                                    st.session_state.current_year_income["mkt_dev"] += 1
                                    if d['progress'] >= d['req']: d['status'] = "已开发"
                                    st.rerun()
                                else: st.error("❌ 现金不足！")
                with col_iso:
                    for i, d in st.session_state.isos.items():
                        if d['status'] != "已认证" and d['last_invest_y'] != st.session_state.year:
                            if st.button(f"投资 {i} (1M) - {d['progress']}/{d['req']}", key=f"i_{i}"):
                                if st.session_state.cash >= 1:
                                    d['progress'] += 1
                                    d['last_invest_y'] = st.session_state.year
                                    log_action("ISO认证", -1, f"投资 {i} ({d['progress']}/{d['req']})")
                                    st.session_state.current_year_income["iso_dev"] += 1
                                    if d['progress'] >= d['req']: d['status'] = "已认证"
                                    st.rerun()
                                else: st.error("❌ 现金不足！")
            else:
                st.info("🕒 市场开拓与ISO认证仅在 **第四季度** 开放。")

            st.divider()
            st.markdown("##### 6. 产品研发")
            for p, d in st.session_state.rnd.items():
                if p != "P1" and d['status'] != "已研发":
                    cc1, cc2 = st.columns([3, 1])
                    cc1.write(f"**{p}** 研发进度: {d['progress']}/{d['req']} (单次投资: **{d['cost']}M**)")
                    if d['last_invest_q'] != get_current_q_str():
                        if cc2.button(f"支付 {d['cost']}M", key=f"r_{p}"):
                            if st.session_state.cash >= d['cost']:
                                d['progress'] += 1
                                d['last_invest_q'] = get_current_q_str()
                                log_action("产品研发", -d['cost'], f"研发 {p} ({d['progress']}/{d['req']})")
                                st.session_state.current_year_income["rnd"] += d['cost']
                                if d['progress'] >= d['req']: d['status'] = "已研发"
                                st.rerun()
                            else: st.error("❌ 现金不足！")
                    else: cc2.success("本季已投")

            st.divider()
            st.markdown("##### 7. 生产线建设推进")
            col_new1, col_new2 = st.columns(2)
            with col_new1: new_line_type = st.selectbox("新建生产线", list(LINE_TYPES.keys()))
            with col_new2:
                st.write("")
                st.write("")
                if st.button("开始建设 (支付 5M)"):
                    if st.session_state.cash >= 5:
                        new_id = (max([l['id'] for l in st.session_state.lines]) + 1) if st.session_state.lines else 1
                        cost = LINE_TYPES[new_line_type]['cost']
                        # 标记 built_year 为当年，确保在当年免收维护费且建成下一年才提折旧
                        st.session_state.lines.append({
                            "id": new_id, "type": new_line_type, "status": "建设中", "product": "未定", 
                            "progress": 1, "invested": 5, "last_invest_q": get_current_q_str(),
                            "book_value": cost, "built_year": st.session_state.year
                        })
                        log_action("新建生产线", -5, f"新增 L{new_id}")
                        if LINE_TYPES[new_line_type]['build_time'] == 1:
                            st.session_state.lines[-1]['status'], st.session_state.lines[-1]['progress'] = "空闲", 0
                        st.rerun()
                    else: st.error("❌ 现金不足！")
                    
            for line in [l for l in st.session_state.lines if l['status'] == "建设中"]:
                b_time = LINE_TYPES[line['type']]['build_time']
                cl1, cl2 = st.columns([3, 1])
                cl1.write(f"**L{line['id']}** ({line['type']}) - 进度 {line['progress']}/{b_time}")
                if line['last_invest_q'] != get_current_q_str():
                    if cl2.button("支付 5M", key=f"inv_{line['id']}"):
                        if st.session_state.cash >= 5:
                            line['progress'] += 1
                            line['invested'] += 5
                            line['last_invest_q'] = get_current_q_str()
                            log_action("推进建设", -5, f"L{line['id']} 建设推进")
                            if line['progress'] >= b_time:
                                line['status'], line['progress'] = "空闲", 0
                                line['built_year'] = st.session_state.year
                            st.rerun()
                        else: st.error("❌ 现金不足！")
                else: cl2.success("本期已付")
                
            st.divider()
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("⬅️ 返回生产环节"):
                    prev_step()
                    st.rerun()
            with cb2:
                if st.button("完成投资，准备结算 ⏭️", type="primary"):
                    next_step()
                    st.rerun()
        elif st.session_state.current_step > 4:
            st.success("本步骤已完成。")

    # ================= 步骤 5 =================
    with st.expander("📍 步骤 5: 季度末状态结算与时间推进", expanded=(st.session_state.current_step == 5)):
        if st.session_state.current_step == 5:
            st.info("点击下方按钮，系统将执行：\n1. 原料到货入库并扣款\n2. 应收账款回收收现\n3. 第四季度自动核算利润税金\n4. 正式迈入下一季度并自动结算下季度产线")
            
            arr_m_check = [o for o in st.session_state.mat_orders if o['arrival_q'] == st.session_state.quarter and o['arrival_y'] == st.session_state.year]
            mat_cost_needed = sum(o['qty'] * 1 for o in arr_m_check) 
            
            if st.session_state.cash < mat_cost_needed:
                st.error(f"⚠️ 预判失败：本季末货船到港，需强制支付原料尾款 {mat_cost_needed}M，当前现金仅余 {st.session_state.cash}M。")
                if st.button("⬅️ 退回步骤1处理现金危机"):
                    st.session_state.current_step = 1
                    st.rerun()
            else:
                cb1, cb2 = st.columns(2)
                with cb1:
                    if st.button("⬅️ 返回投资环节"):
                        prev_step()
                        st.rerun()
                with cb2:
                    if st.button("🏁 结算本季度，推进时间", type="primary", use_container_width=True):
                        
                        # 1. 原料到货入库并扣款
                        arr_m = [o for o in st.session_state.mat_orders if o['arrival_q'] == st.session_state.quarter and o['arrival_y'] == st.session_state.year]
                        for o in arr_m:
                            st.session_state.materials[o['mat']] += o['qty']
                            log_action("原料到货入库", -(o['qty'] * 1), f"{o['qty']}个{o['mat']}入库 (现库存: {st.session_state.materials[o['mat']]})")
                        st.session_state.mat_orders = [o for o in st.session_state.mat_orders if o not in arr_m]
                        
                        # 2. 应收账款回收
                        arr_r = [r for r in st.session_state.receivables if r['arrival_q'] == st.session_state.quarter and r['arrival_y'] == st.session_state.year]
                        for r in arr_r: 
                            log_action("应收账款收现", r['amount'], "账期到达")
                        st.session_state.receivables = [r for r in st.session_state.receivables if r not in arr_r]

                        # 3. 年末核算利润
                        if st.session_state.quarter == 4:
                            inc = st.session_state.current_year_income
                            comprehensive = (inc["admin"] + inc["rent"] + inc["mkt_maint"] + inc["maint"] + 
                                             inc["ad"] + inc["mkt_dev"] + inc["iso_dev"] + inc["rnd"] + inc["switch"] + inc["asset_loss"])
                            profit_before_tax = inc["revenue"] - inc["direct_cost"] - comprehensive - inc["depreciation"] - inc["financial"]
                            tax = profit_before_tax // 3 if profit_before_tax > 0 else 0
                            
                            st.session_state.tax_payable = tax
                            log_action("利润核算", 0, f"税前利润: {profit_before_tax}M，次年应交税: {tax}M")
                            st.session_state.current_year_income = {k: 0 for k in st.session_state.current_year_income}
                        
                        # 记录流水并弹出弹窗
                        curr_q_flows = [f for f in st.session_state.cash_flows if f['年份'] == st.session_state.year and f['季度'] == st.session_state.quarter]
                        st.session_state.last_q_flows = curr_q_flows
                        st.session_state.last_q_str = get_current_q_str()
                        st.session_state.show_q_summary = True
                        
                        # 时间推进并重置标志位
                        st.session_state.quarter += 1
                        st.session_state.quarter_fees_paid = False 
                        st.session_state.quarter_production_advanced = False
                        if st.session_state.quarter > 4:
                            st.session_state.quarter = 1
                            st.session_state.year += 1
                        
                        st.session_state.current_step = 1
                        st.rerun()

# ==================== 面板 2：报表 ====================
with tab_reports:
    st.subheader("💰 资金流动与折旧中台")
    if not st.session_state.cash_flows:
        st.info("当前尚未产生记录。")
    else:
        df_flows = pd.DataFrame(st.session_state.cash_flows)
        available_years = sorted(df_flows["年份"].unique().tolist())
        col_r1, col_r2 = st.columns(2)
        with col_r1: select_year = st.selectbox("查询年份", available_years)
        with col_r2: select_view = st.selectbox("报表视图", ["年度汇总总表", "第一季度", "第二季度", "第三季度", "第四季度"])
            
        df_year = df_flows[df_flows["年份"] == select_year]
        if select_view == "年度汇总总表":
            st.dataframe(df_year, use_container_width=True, hide_index=True)
            t_in = df_year[df_year["收支金额(M)"] > 0]["收支金额(M)"].sum()
            t_out = df_year[df_year["收支金额(M)"] < 0]["收支金额(M)"].sum()
            st.metric(label="全年净现金流", value=f"{t_in + t_out} M", delta=f"总入: {t_in}M | 总出: {t_out}M")
            year_dep = sum(d['amount'] for d in st.session_state.depreciation_log if d['year'] == select_year)
            st.write(f"***注：本年度共计提非现金折旧 {year_dep}M***")
        else:
            q_map = {"第一季度": 1, "第二季度": 2, "第三季度": 3, "第四季度": 4}
            df_q = df_year[df_year["季度"] == q_map[select_view]]
            if df_q.empty: st.write("该季度无现金记录。")
            else:
                st.dataframe(df_q, use_container_width=True, hide_index=True)
                q_in = df_q[df_q["收支金额(M)"] > 0]["收支金额(M)"].sum()
                q_out = df_q[df_q["收支金额(M)"] < 0]["收支金额(M)"].sum()
                st.metric(label="当季净流", value=f"{q_in + q_out} M", delta=f"入: {q_in}M | 出: {q_out}M")

with tab_log:
    st.text_area("复制存档：", "\n".join(st.session_state.log), height=400)
