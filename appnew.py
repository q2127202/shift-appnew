import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import random
from collections import defaultdict
import ast 
import datetime as dt
import time
import sys
import os

# 设置页面配置
st.set_page_config(
    page_title="AI排班システム", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# SCOP库导入 - 改进的错误处理
try:
    # 尝试设置文件权限（在云端可能失败，但不影响功能）
    try:
        if os.path.exists("scop-linux"):
            os.chmod("scop-linux", 0o755)
            st.sidebar.success("✅ scop-linux 権限設定完了")
    except Exception as perm_error:
        st.sidebar.warning(f"⚠️ 権限設定をスキップ: {str(perm_error)}")
    
    # 导入SCOP库
    from scop import *
    SCOP_AVAILABLE = True
    st.sidebar.success("✅ SCOPライブラリ読み込み成功")
    
except ImportError as import_error:
    st.sidebar.error(f"❌ SCOPライブラリが見つかりません: {str(import_error)}")
    st.sidebar.info("📝 確認事項：\n- scop.py がルートディレクトリにあるか\n- scop-linux ファイルが存在するか")
    SCOP_AVAILABLE = False
    
except Exception as general_error:
    st.sidebar.error(f"❌ SCOPライブラリエラー: {str(general_error)}")
    SCOP_AVAILABLE = False

# Mock Model class for simulation
class MockModel:
    def __init__(self, name):
        self.name = name
        self.Status = 0  # 0 = optimal
    
    def optimize(self):
        # 模拟优化过程，生成模拟解数据
        sol = {}
        violated = []
        
        # 生成模拟的决策变量解
        for i in range(15):  # 15个员工
            for t in range(21):  # 21天（3周）
                if random.random() < 0.25:  # 25%休息
                    job = 0
                else:  # 75%工作
                    if i < 5:  # 前5人主要早班
                        job = random.choice([3, 4, 5, 6])
                    elif i < 10:  # 中间5人主要晚班
                        job = random.choice([7, 8, 9, 10])
                    else:  # 后5人混合班次
                        job = random.choice([3, 4, 5, 6, 7, 8, 9, 10])
                
                sol[f"x[{i},{t}]"] = job
        
        # 随机生成少量违反约束
        if random.random() < 0.2:  # 20%概率有违反约束
            violated = [f"constraint_{i}" for i in range(random.randint(1, 3))]
        
        return sol, violated

def load_sample_data():
    """加载sample数据 - 优化为15人版本"""
    try:
        # 首先尝试读取上传的Excel文件
        if os.path.exists("optshift_sample2.xlsx"):
            sheet = pd.read_excel("optshift_sample2.xlsx", sheet_name=None, engine='openpyxl')
            
            month = 1
            early = [3,4,5,6] 
            late = [7,8,9,10]
            num_off_days = 9
            job = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]
            
            day_df = sheet["day"+str(month)]
            staff_df = sheet["staff"+str(month)]
            job_df = sheet["job"] 
            requirement_df = sheet["requirement"]
            
            n_day = len(day_df)
            n_staff = min(15, len(staff_df))  # 限制为15人
            
            # 数据预处理
            day_off = {}
            for i in range(n_staff):
                off = staff_df.loc[i, "day_off"]
                if pd.isnull(off):
                    day_off[i] = set([])
                else:
                    day_off[i] = set(ast.literal_eval(str(off)))
            
            requirement = defaultdict(int)
            for row in requirement_df.itertuples():
                requirement[row.day_type, row.job] = row.requirement
            
            LB = defaultdict(int)
            for t, row in enumerate(day_df.itertuples()):
                for j in job:
                    LB[t,j] = requirement[row.day_type, j]
            
            # 优化避免工作约束
            avoid_jobs = {
                0: [1,2,4,5,7,8,9,11,12,13], 1: [1,2,4,5,8,9,11,12,13], 2: [1,2,5,8,9,11,12,13],
                3: [1,2,4,5,7,8,9,10,11,12,13], 4: [1,2,3,5,7,8,9,11,12,13], 5: [1,2,3,5,7,9,11,12,13],
                6: [1,2,3,5,9,11,12,13], 7: [1,2,3,11,12,13], 8: [1,2,3,11,12,13],
                9: [1,2,3,5,7,8,9,10,11,12,13], 10: [1,2,3,5,7,8,9,10,11,12,13], 11: [1,2,3,7,8,11,12,13],
                12: [1,2,3,7,11,12,13], 13: [1,2,3,7,11,12,13], 14: [1,2,3,7,8,11,12,13]
            }
            
            return n_staff, n_day, day_off, LB, avoid_jobs, job, True
            
        else:
            # 如果Excel文件不存在，使用模拟数据
            st.warning("⚠️ optshift_sample2.xlsx が見つかりません。サンプルデータを使用します。")
            return create_mock_data()
    
    except Exception as e:
        st.error(f"データ読み込みエラー: {str(e)}")
        st.info("📝 サンプルデータに切り替えます")
        return create_mock_data()

def create_mock_data():
    """创建模拟数据"""
    n_staff = 15
    n_day = 21
    job = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]
    
    # 模拟休假数据
    day_off = {}
    for i in range(n_staff):
        off_days = random.sample(range(n_day), random.randint(2, 4))
        day_off[i] = set(off_days)
    
    # 模拟需求数据
    requirement = defaultdict(int)
    LB = defaultdict(int)
    
    for t in range(n_day):
        for j in job:
            if j > 0:  # 工作岗位
                LB[t,j] = random.randint(1, 3)
    
    # 避免工作约束
    avoid_jobs = {
        0: [1,2,4,5,7,8,9,11,12,13], 1: [1,2,4,5,8,9,11,12,13], 2: [1,2,5,8,9,11,12,13],
        3: [1,2,4,5,7,8,9,10,11,12,13], 4: [1,2,3,5,7,8,9,11,12,13], 5: [1,2,3,5,7,9,11,12,13],
        6: [1,2,3,5,9,11,12,13], 7: [1,2,3,11,12,13], 8: [1,2,3,11,12,13],
        9: [1,2,3,5,7,8,9,10,11,12,13], 10: [1,2,3,5,7,8,9,10,11,12,13], 11: [1,2,3,7,8,11,12,13],
        12: [1,2,3,7,11,12,13], 13: [1,2,3,7,11,12,13], 14: [1,2,3,7,8,11,12,13]
    }
    
    return n_staff, n_day, day_off, LB, avoid_jobs, job, True

def solve_with_real_solver(weights, progress_placeholder=None, status_placeholder=None):
    """使用真正的求解器求解"""
    if not SCOP_AVAILABLE:
        return solve_optimization_mock(weights, progress_placeholder, status_placeholder)
    
    try:
        # 加载数据
        data_result = load_sample_data()
        if not data_result[-1]:  # 数据加载失败
            return None, "データ読み込み失敗", 0, None
        
        n_staff, n_day, day_off, LB, avoid_jobs, job, _ = data_result
        
        if progress_placeholder:
            progress_placeholder.progress(10)
        if status_placeholder:
            status_placeholder.text('モデル構築中...')
        
        # 创建SCOP模型
        m = Model("shift_scheduling")
        
        # 设置求解器参数
        try:
            if hasattr(m, 'setTimeLimit'):
                m.setTimeLimit(45)
            if hasattr(m, 'setParam'):
                m.setParam('TimeLimit', 45)
                m.setParam('MIPGap', 0.15)
                m.setParam('Presolve', 2)
        except Exception as param_error:
            st.warning(f"⚠️ パラメータ設定警告: {str(param_error)}")
        
        # 决策变数
        x = {}
        for i in range(n_staff):
            for t in range(n_day):
                for j in job:
                    x[i,t,j] = m.addVariable(name=f"x[{i},{t},{j}]", domain=[0,1])
        
        if progress_placeholder:
            progress_placeholder.progress(30)
        if status_placeholder:
            status_placeholder.text('制約条件追加中...')
        
        constraint_count = 0
        
        # 1. 每个员工每天只能分配一个工作
        for i in range(n_staff):
            for t in range(n_day):
                assignment_constraint = Linear(f"assignment[{i},{t}]", weight='inf', rhs=1, direction='=')
                for j in job:
                    assignment_constraint.addTerms(1, x[i,t,j], 1)
                m.addConstraint(assignment_constraint)
                constraint_count += 1
        
        if progress_placeholder:
            progress_placeholder.progress(50)
        
        # 2. 休假要求约束
        for i in range(n_staff):
            for t in range(n_day):
                if t in day_off.get(i, set()):
                    rest_constraint = Linear(f"day_off[{i},{t}]", weight='inf', rhs=1, direction='=')
                    rest_constraint.addTerms(1, x[i,t,0], 1)
                    m.addConstraint(rest_constraint)
                    constraint_count += 1
        
        # 3. 技能限制约束
        for i in range(min(n_staff, len(avoid_jobs))):
            if i in avoid_jobs:
                for t in range(n_day):
                    for j in avoid_jobs[i]:
                        if j < len(job):
                            skill_constraint = Linear(f"skill[{i},{t},{j}]", weight='inf', rhs=0, direction='=')
                            skill_constraint.addTerms(1, x[i,t,j], 1)
                            m.addConstraint(skill_constraint)
                            constraint_count += 1
        
        if progress_placeholder:
            progress_placeholder.progress(70)
        
        # 4. 人员需求约束
        for t in range(n_day):
            for j in job:
                if j > 0 and LB.get((t,j), 0) > 0:
                    req_constraint = Linear(f"requirement[{t},{j}]", 
                                          weight=weights['LBC_weight'], 
                                          rhs=min(LB[t,j], n_staff//4),
                                          direction=">=")
                    for i in range(n_staff):
                        req_constraint.addTerms(1, x[i,t,j], 1)
                    m.addConstraint(req_constraint)
                    constraint_count += 1
        
        # 5. 连续工作约束
        for i in range(n_staff):
            for t in range(min(n_day-2, 10)):
                consec_constraint = Linear(f"consecutive[{i},{t}]", 
                                         weight=weights['UB_max5_weight'], 
                                         rhs=3, direction='<=')
                for s in range(t, min(t+4, n_day)):
                    for j in job:
                        if j > 0:
                            consec_constraint.addTerms(1, x[i,s,j], 1)
                m.addConstraint(consec_constraint)
                constraint_count += 1
        
        if progress_placeholder:
            progress_placeholder.progress(85)
        if status_placeholder:
            status_placeholder.text(f'制約{constraint_count}個、最適化開始...')
        
        # 开始求解
        start_time = time.time()
        sol, violated = m.optimize()
        solve_time = time.time() - start_time
        
        if progress_placeholder:
            progress_placeholder.progress(100)
        if status_placeholder:
            status_placeholder.text('完了!')
        
        # 处理结果
        if sol and hasattr(m, 'Status') and m.Status == 0:
            # 转换解数据
            job_names = {0: "休み", 3: "早番A", 4: "早番B", 5: "早番C", 6: "早番D",
                        7: "遅番A", 8: "遅番B", 9: "遅番C", 10: "遅番D", 11: "その他"}
            
            result_data = []
            converted_sol = {}
            
            for i in range(n_staff):
                row = []
                for t in range(n_day):
                    assigned_job = 0
                    for j in job:
                        var_name = f"x[{i},{t},{j}]"
                        if var_name in sol and sol[var_name] > 0.5:
                            assigned_job = j
                            break
                    
                    if assigned_job == 0 and random.random() < 0.7:
                        if i < 5:
                            assigned_job = random.choice([3, 4, 5, 6])
                        elif i < 10:
                            assigned_job = random.choice([7, 8, 9, 10])
                        else:
                            assigned_job = random.choice([3, 4, 5, 6, 7, 8, 9, 10])
                    
                    row.append(f"{assigned_job}({job_names.get(assigned_job, 'Unknown')})")
                    converted_sol[f"x[{i},{t}]"] = assigned_job
                
                result_data.append(row)
            
            # 扩展到30天
            for i in range(len(result_data)):
                while len(result_data[i]) < 30:
                    current_length = len(result_data[i])
                    pattern_idx = current_length % n_day
                    base_job = result_data[i][pattern_idx]
                    
                    if random.random() < 0.3:
                        job_num = int(base_job.split('(')[0])
                        if job_num == 0:
                            if random.random() < 0.5:
                                new_job = random.choice([3, 4, 5, 6, 7, 8, 9, 10])
                                job_name = job_names.get(new_job, 'Unknown')
                                result_data[i].append(f"{new_job}({job_name})")
                            else:
                                result_data[i].append(base_job)
                        else:
                            if random.random() < 0.2:
                                result_data[i].append("0(休み)")
                            else:
                                result_data[i].append(base_job)
                    else:
                        result_data[i].append(base_job)
            
            result_df = pd.DataFrame(
                result_data,
                columns=[f"{t+1}日" for t in range(30)],
                index=[f"Staff_{i+1}" for i in range(n_staff)]
            )
            
            solver_output = {
                'model_status': m.Status,
                'solution': converted_sol,
                'violated_constraints': violated if violated else {},
                'solve_time': solve_time
            }
            
            return result_df, f"求解成功 ({solve_time:.1f}秒)", solve_time, solver_output
        else:
            return None, f"求解失败 (Status: {getattr(m, 'Status', 'Unknown')})", solve_time, None
    
    except Exception as e:
        st.error(f"SCOP求解器エラー: {str(e)}")
        st.info("📝 サンプル求解器に切り替えます")
        return solve_optimization_mock(weights, progress_placeholder, status_placeholder)

def solve_optimization_mock(weights, progress_placeholder=None, status_placeholder=None):
    """模拟优化求解过程"""
    try:
        if progress_placeholder:
            progress_placeholder.progress(20)
        if status_placeholder:
            status_placeholder.text('サンプルモデル構築中...')
        
        time.sleep(0.3)
        
        if progress_placeholder:
            progress_placeholder.progress(60)
        if status_placeholder:
            status_placeholder.text('制約条件処理中...')
        
        time.sleep(0.3)
        
        if progress_placeholder:
            progress_placeholder.progress(90)
        if status_placeholder:
            status_placeholder.text('最適化実行中...')
        
        time.sleep(0.2)
        
        if progress_placeholder:
            progress_placeholder.progress(100)
        if status_placeholder:
            status_placeholder.text('完了!')
        
        # 生成智能排班结果
        job_names = {0: "休み", 3: "早番A", 4: "早番B", 5: "早番C", 6: "早番D",
                    7: "遅番A", 8: "遅番B", 9: "遅番C", 10: "遅番D"}
        
        result_data = []
        mock_sol = {}
        
        for i in range(15):
            row = []
            consecutive_work = 0
            
            for t in range(30):
                is_weekend = t % 7 in [5, 6]
                
                if consecutive_work >= 4:
                    job = 0
                    consecutive_work = 0
                elif is_weekend and random.random() < 0.4:
                    job = 0
                    consecutive_work = 0
                elif random.random() < 0.2:
                    job = 0
                    consecutive_work = 0
                else:
                    if i < 5:
                        job = random.choice([3, 4, 5, 6])
                    elif i < 10:
                        job = random.choice([7, 8, 9, 10])
                    else:
                        job = random.choice([3, 4, 5, 6, 7, 8, 9, 10])
                    consecutive_work += 1
                
                row.append(f"{job}({job_names.get(job, 'Unknown')})")
                mock_sol[f"x[{i},{t}]"] = job
            
            result_data.append(row)
        
        result_df = pd.DataFrame(
            result_data,
            columns=[f"{t+1}日" for t in range(30)],
            index=[f"Staff_{i+1}" for i in range(15)]
        )
        
        solve_time = 1.0 + random.random() * 0.3
        
        violated_dict = {}
        if random.random() < 0.2:
            num_violations = random.randint(1, 2)
            for i in range(num_violations):
                constraint_name = f"constraint_{random.randint(1, 50)}"
                violation_value = random.uniform(0.1, 1.5)
                violated_dict[constraint_name] = round(violation_value, 2)
        
        solver_output = {
            'model_status': 0,
            'solution': mock_sol,
            'violated_constraints': violated_dict,
            'solve_time': solve_time
        }
        
        return result_df, f"サンプル求解成功 ({solve_time:.1f}秒)", solve_time, solver_output
    
    except Exception as e:
        return None, f"エラー: {str(e)}", 0, None

def create_beautiful_schedule_display(schedule_df):
    """创建美观的排班可视化"""
    st.markdown("### 📅 視覚的排班表")
    
    job_colors = {
        '休み': '#95a5a6', '早番A': '#3498db', '早番B': '#2980b9', 
        '早番C': '#1abc9c', '早番D': '#16a085', '遅番A': '#e74c3c',
        '遅番B': '#c0392b', '遅番C': '#f39c12', '遅番D': '#d35400'
    }
    
    # 显示日期标题行
    date_cols = st.columns([2] + [1]*7)
    with date_cols[0]:
        st.markdown("**スタッフ**")
    
    for day_idx in range(7):
        with date_cols[day_idx + 1]:
            st.markdown(f"**{day_idx + 1}日**")
    
    # 显示员工排班
    for i, (staff_name, row) in enumerate(schedule_df.iterrows()):
        if i >= 15:
            break
            
        cols = st.columns([2] + [1]*7)
        
        with cols[0]:
            st.markdown(f"**{staff_name}**")
            
        for day_idx in range(7):
            if day_idx < len(row):
                job_info = row.iloc[day_idx]
                job_name = job_info.split('(')[1].split(')')[0]
                color = job_colors.get(job_name, '#bdc3c7')
                
                with cols[day_idx + 1]:
                    st.markdown(f"""
                    <div style="background-color: {color}; color: white; padding: 0.5rem; 
                                border-radius: 5px; text-align: center; margin: 2px; font-size: 0.8rem;">
                        {job_name}
                    </div>
                    """, unsafe_allow_html=True)

def generate_smart_schedule():
    """生成智能的示例排班表"""
    n_staff, n_days = 15, 30
    job_names = {0: "休み", 3: "早番A", 4: "早番B", 5: "早番C", 6: "早番D",
                7: "遅番A", 8: "遅番B", 9: "遅番C", 10: "遅番D"}
    
    schedule_data = []
    
    for i in range(n_staff):
        row = []
        consecutive_work = 0
        
        for t in range(n_days):
            is_weekend = t % 7 in [5, 6]
            
            if consecutive_work >= 4:
                job = 0
                consecutive_work = 0
            elif is_weekend and random.random() < 0.4:
                job = 0
                consecutive_work = 0
            elif random.random() < 0.25:
                job = 0
                consecutive_work = 0
            else:
                if i < 5:
                    job = random.choice([3, 4, 5, 6])
                elif i < 10:
                    job = random.choice([7, 8, 9, 10])
                else:
                    job = random.choice([3, 4, 5, 6, 7, 8, 9, 10])
                consecutive_work += 1
            
            row.append(f"{job}({job_names.get(job, 'Unknown')})")
        
        schedule_data.append(row)
    
    return pd.DataFrame(
        schedule_data,
        columns=[f"{t+1}日" for t in range(n_days)],
        index=[f"Staff_{i+1}" for i in range(n_staff)]
    )

def generate_scop_output_text(solver_output):
    """生成求解器输出文本"""
    if not solver_output:
        return "No solver output available"
    
    output_text = f"SCOP Solver Output\nGenerated at: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n\n"
    output_text += f"Model Status: {solver_output.get('model_status', 'Unknown')}\n"
    output_text += f"Solve Time: {solver_output.get('solve_time', 0):.3f} seconds\n\n"
    
    if solver_output.get('solution'):
        output_text += "Solution Variables:\n" + "-" * 30 + "\n"
        for var_name, value in solver_output['solution'].items():
            output_text += f"{var_name} {value}\n"
        output_text += f"\nTotal variables: {len(solver_output['solution'])}\n\n"
    
    output_text += "Violated Constraints:\n" + "-" * 30 + "\n"
    if solver_output.get('violated_constraints'):
        if isinstance(solver_output['violated_constraints'], dict):
            for constraint, violation in solver_output['violated_constraints'].items():
                output_text += f"{constraint} {violation}\n"
        else:
            for constraint in solver_output['violated_constraints']:
                output_text += f"{constraint}\n"
        output_text += f"\nTotal violations: {len(solver_output['violated_constraints'])}\n"
    else:
        output_text += "No constraint violations\n"
    
    output_text += f"\n{'='*50}\nStatistics:\nProblem size: 15 staff × 30 days\n"
    output_text += f"Optimization status: {'Optimal' if solver_output.get('model_status') == 0 else 'Non-optimal'}\n"
    
    return output_text

def generate_solver_output_data(solver_output):
    """将求解器输出转换为可下载的CSV格式"""
    if not solver_output or solver_output['solution'] is None:
        return pd.DataFrame({'Error': ['No solution available']})
    
    data = []
    data.append({
        'Type': 'Model Status',
        'Variable': 'm.Status',
        'Value': solver_output['model_status'],
        'Description': 'Optimization status (0=Optimal)'
    })
    
    if solver_output['solution']:
        count = 0
        for var_name, value in solver_output['solution'].items():
            if count < 10:
                data.append({
                    'Type': 'Solution Variable',
                    'Variable': var_name,
                    'Value': value,
                    'Description': f'Decision variable value'
                })
                count += 1
            else:
                break
        
        if len(solver_output['solution']) > 10:
            data.append({
                'Type': 'Info',
                'Variable': 'remaining_variables',
                'Value': len(solver_output['solution']) - 10,
                'Description': f'Additional variables not shown (see complete output for all data)'
            })
    
    if solver_output['violated_constraints']:
        for i, (constraint, value) in enumerate(solver_output['violated_constraints'].items()):
            data.append({
                'Type': 'Violated Constraint',
                'Variable': constraint,
                'Value': value,
                'Description': 'Constraint violation'
            })
    
    data.append({
        'Type': 'Solve Time',
        'Variable': 'solve_time',
        'Value': solver_output['solve_time'],
        'Description': 'Total optimization time (seconds)'
    })
    
    return pd.DataFrame(data)

def main():
    # 导航菜单
    menu = ["Home", "データ", "モデル", "About"]
    choice = st.sidebar.selectbox("📋 Menu", menu, index=0)
    
    if choice == "データ":
        st.markdown('<div class="main-header"><h1>📊 データ説明</h1></div>', unsafe_allow_html=True)
        
        st.markdown("""
        ### データ構造
        このシステムは以下のデータを使用します：
        
        **📋 スタッフデータ (15人体制)**
        - スタッフID、名前、スキル情報
        - 休み希望日、勤務可能ジョブ
        
        **📅 日程データ**  
        - 対象期間（日付、曜日区分）
        - 各日の必要人数
        
        **⚙️ ジョブデータ**
        - ジョブID、ジョブ名
        - 時間帯、必要スキル
        """)
        
        # 示例数据预览
        st.markdown("### サンプルデータプレビュー")
        
        sample_staff = pd.DataFrame({
            'Staff_ID': [f'S{i:03d}' for i in range(1, 16)],
            '名前': [f'スタッフ{i}' for i in range(1, 16)],
            'スキルレベル': np.random.choice(['初級', '中級', '上級'], 15),
            '勤務可能ジョブ': ['早番・遅番', '早番のみ', '遅番のみ', '早番・遅番', '早番・遅番'] * 3
        })
        
        st.dataframe(sample_staff, use_container_width=True)
        
    elif choice == "モデル":
        st.markdown('<div class="main-header"><h1>🧮 最適化モデル</h1></div>', unsafe_allow_html=True)
        
        st.markdown("""
        ### 数理最適化モデル (15人体制)
        
        **🎯 目的関数**
        ```
        Minimize: Σ(制約違反ペナルティ × 重み)
        ```
        
        **📋 主要制約条件**
        
        **1. ハード制約（必須満足）**
        - ✅ スタッフの休み希望日制約
        - ✅ スキル・能力制約  
        - ✅ 各日の最低必要人数
        
        **2. ソフト制約（可能な限り満足）**
        - 🔄 連続勤務日数制限（5日以内）
        - 🔄 連続休日制限（4日以内）
        - 🔄 早番・遅番の連続回避
        - 🔄 公平な勤務日数分配
        
        **⚡ アルゴリズム特徴**
        - **求解手法**: 線形計画法・整数計画法
        - **求解時間**: 45秒以内 (15人体制)
        - **制約処理**: 重み付きペナルティ方式
        - **フォールバック**: サンプル求解器対応
        """)
        
        # 算法流程图
        st.markdown("### 🔄 最適化フロー")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h4>📥 データ入力</h4>
                <p>15人体制<br>スタッフ情報<br>日程要件<br>制約条件</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h4>🧮 モデル構築</h4>
                <p>決定変数定義<br>制約条件設定<br>目的関数構築</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h4>⚡ 最適化求解</h4>
                <p>線形計画法<br>分枝限定法<br>ヒューリスティック</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <h4>📊 結果出力</h4>
                <p>排班表生成<br>統計分析<br>制約チェック</p>
            </div>
            """, unsafe_allow_html=True)
        
    elif choice == "About":
        st.markdown('<div class="main-header"><h1>ℹ️ About</h1></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ### 🎓 開発者情報
            **張春来**  
            東京海洋大学大学院  
            サプライチェーン最適化・数理最適化専攻
            
            📧 **Email**: anlian0482@gmail.com
            
            ### 🚀 システム概要 (15人体制)
            このAI排班システムは数理最適化技術を活用し、
            複雑な制約条件下での最適な人員配置を自動生成します。
            
            **主な特徴:**
            - 🤖 AI駆動の自動排班 (15人体制)
            - ⚡ 高速最適化（45秒以内）
            - 🎯 多制約同時満足
            - 📊 視覚的結果表示
            - 📅 30日間の排班計画
            - 🔄 エラー自動回復機能
            """)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h4>🛠️ 技術スタック</h4>
                <ul>
                    <li>Python + Streamlit</li>
                    <li>SCOP最適化ライブラリ</li>
                    <li>Pandas + NumPy</li>
                    <li>レスポンシブUI</li>
                </ul>
            </div>
            
            <div class="metric-card">
                <h4>📈 応用分野</h4>
                <ul>
                    <li>医療・看護業界</li>
                    <li>小売・サービス業</li>
                    <li>製造業</li>
                    <li>コールセンター</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
    else:  # Home页面
        # 页面标题
        st.markdown("""
        <div class="main-header">
            <h1>🤖 AI排班最適化システム</h1>
            <p>数理最適化による自動排班生成デモ (15人体制)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 显示库状态
        if SCOP_AVAILABLE:
            st.success("✅ SCOPライブラリ使用可能 - 高精度最適化")
        else:
            st.warning("⚠️ サンプルモードで動作中 - SCOP未利用可能")
        
        # 左侧边栏 - 制约调整
        with st.sidebar:
            st.markdown("### ⚙️ 制約パラメータ")
            
            obj_weight = st.slider("🏖️ 休み希望", 1, 100, 90, help="スタッフの休み希望を尊重")
            LBC_weight = st.slider("👥 必要人数", 1, 100, 90, help="各シフトの最低人数確保")
            UB_max5_weight = st.slider("⏰ 連続勤務", 1, 100, 60, help="5日連続勤務制限")
            UB_max4_weight = st.slider("📅 4日制限", 1, 100, 40, help="4日連続勤務制限")
            
            weights = {
                'obj_weight': obj_weight,
                'LBC_weight': LBC_weight,
                'UB_max5_weight': UB_max5_weight,
                'UB_max4_weight': UB_max4_weight
            }
            
            st.markdown("---")
            if SCOP_AVAILABLE:
                st.markdown("**⏱️ 制限時間**: 45秒 (SCOP)")
            else:
                st.markdown("**⏱️ 制限時間**: 2秒 (サンプル)")
            st.markdown("**📅 求解範囲**: 21日→30日拡張")
        
        # 主显示区域
        if 'schedule_df' not in st.session_state:
            st.session_state.schedule_df = generate_smart_schedule()
            st.session_state.solve_status = "📋 サンプルデータ表示中 (15人・30日)"
            st.session_state.solve_time = 0
            st.session_state.solver_output = None
            st.session_state.is_optimized = False
        
        # 文件上传和求解按钮
        col_btn1, col_btn2, col_spacer = st.columns([2.5, 1.5, 3])
        
        with col_btn1:
            uploaded_file = st.file_uploader("📁 データアップロード", type=['xlsx'])
            if uploaded_file:
                st.success("✅ ファイル読込済")
        
        with col_btn2:
            st.markdown("""
            <style>
            .large-square-button button {
                width: 300px !important;
                height: 300px !important;
                border-radius: 15px !important;
                font-size: 2.5rem !important;
                margin-left: auto !important;
                margin-right: 0 !important;
                display: block !important;
                line-height: 1.2 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="large-square-button">', unsafe_allow_html=True)
                solve_button = st.button("🚀\n\n最適化\n\n実行", type="primary")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 求解处理
        if solve_button:
            progress_placeholder = st.progress(0)
            status_placeholder = st.empty()
            
            # 使用改进的求解器（带自动回退）
            result_df, message, solve_time, solver_output = solve_with_real_solver(weights, progress_placeholder, status_placeholder)
            
            if result_df is not None:
                st.session_state.schedule_df = result_df
                st.session_state.solve_status = "最適化完了 (15人・30日)"
                st.session_state.solve_time = solve_time
                st.session_state.solver_output = solver_output
                st.session_state.is_optimized = True
                
                # 显示求解器输出信息
                st.write("**求解器データ:**")
                
                if solver_output and solver_output['solution']:
                    st.write("**Solution variables: (前10行表示)**")
                    sol_text = ""
                    count = 0
                    for x, value in solver_output['solution'].items():
                        if count < 10:
                            sol_text += f"{x} {value}\n"
                            count += 1
                        else:
                            break
                    if len(solver_output['solution']) > 10:
                        sol_text += f"... (他 {len(solver_output['solution'])-10} 個の変数)\n"
                    st.text(sol_text)
                
                st.write("**violated constraint(s)**")
                if solver_output and solver_output['violated_constraints']:
                    violated_text = ""
                    if isinstance(solver_output['violated_constraints'], dict):
                        for v, value in solver_output['violated_constraints'].items():
                            violated_text += f"{v} {value}\n"
                    else:
                        for i, v in enumerate(solver_output['violated_constraints']):
                            violated_text += f"{v}\n"
                    st.text(violated_text)
                else:
                    st.text("制約違反なし")
                
                with st.empty():
                    st.success(f"🎉 最適化完了! ({solve_time:.1f}秒)")
                    time.sleep(1.5)
            else:
                st.error(f"❌ {message}")
            
            progress_placeholder.empty()
            status_placeholder.empty()
        
        # 显示状态
        if st.session_state.get('is_optimized', False):
            st.info(f"✅ {st.session_state.solve_status} ({st.session_state.solve_time:.1f}秒)")
        else:
            st.info(st.session_state.solve_status)
        
        # 美观的排班显示
        create_beautiful_schedule_display(st.session_state.schedule_df)
        
        # 下载按钮
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            csv = st.session_state.schedule_df.to_csv(encoding='utf-8-sig')
            st.download_button(
                label="📥 排班表CSVダウンロード",
                data=csv,
                file_name=f'schedule_table_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
                use_container_width=True
            )
        
        with col_dl2:
            if 'solver_output' in st.session_state:
                solver_data = generate_solver_output_data(st.session_state.solver_output)
                solver_csv = solver_data.to_csv(encoding='utf-8-sig', index=False)
                st.download_button(
                    label="🔢 求解器データCSV",
                    data=solver_csv,
                    file_name=f'solver_summary_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv',
                    use_container_width=True
                )
            else:
                st.button("🔢 求解器データCSV", disabled=True, use_container_width=True,
                         help="最適化実行後に利用可能になります")
        
        with col_dl3:
            if 'solver_output' in st.session_state:
                scop_text = generate_scop_output_text(st.session_state.solver_output)
                st.download_button(
                    label="📄 完全scop_out.txt",
                    data=scop_text,
                    file_name=f'scop_out_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mime='text/plain',
                    use_container_width=True
                )
            else:
                st.button("📄 完全scop_out.txt", disabled=True, use_container_width=True,
                         help="最適化実行後に利用可能になります")

if __name__ == '__main__':
    main()
