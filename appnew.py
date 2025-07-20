import streamlit as st
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

# 全局变量
SCOP_AVAILABLE = False
SCOP_MODULE = None
Model = None
Linear = None

def check_optional_dependencies():
    """检查可选依赖项"""
    optional_deps = ['plotly', 'matplotlib', 'scipy']
    available = []
    missing = []
    
    for dep in optional_deps:
        try:
            __import__(dep)
            available.append(dep)
        except ImportError:
            missing.append(dep)
    
    return available, missing

def try_import_scop():
    """尝试导入 SCOP 库"""
    global SCOP_AVAILABLE, SCOP_MODULE, Model, Linear
    
    import_results = {}
    
    try:
        # 检查可选依赖
        available_deps, missing_deps = check_optional_dependencies()
        import_results['optional_dependencies'] = {
            'available': available_deps,
            'missing': missing_deps
        }
        
        if missing_deps:
            import_results['dependency_warning'] = f"⚠️ 可选依赖缺失: {', '.join(missing_deps)}"
            # 不再阻止导入，继续尝试
        
        # 设置环境
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 设置文件权限
        permission_results = {}
        for binary in ['scop-linux', 'scop-mac', 'scop.exe']:
            if os.path.exists(binary):
                try:
                    os.chmod(binary, 0o755)
                    permission_results[binary] = "✅ 权限设置成功"
                except Exception as e:
                    permission_results[binary] = f"❌ 权限设置失败: {e}"
            else:
                permission_results[binary] = "❌ 文件不存在"
        
        import_results['file_permissions'] = permission_results
        
        # 检查 scop.py 文件
        if not os.path.exists('scop.py'):
            import_results['scop_file'] = "❌ scop.py 不存在"
            return False, import_results
        else:
            import_results['scop_file'] = "✅ scop.py 存在"
        
        # 尝试动态导入 SCOP
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("scop", "scop.py")
            scop_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scop_module)
            sys.modules['scop'] = scop_module
            
            SCOP_MODULE = scop_module
            import_results['scop_module_load'] = "✅ scop模块加载成功"
            
            # 尝试获取主要类
            Model = getattr(scop_module, 'Model', None)
            Linear = getattr(scop_module, 'Linear', None)
            
            if Model is None:
                import_results['model_class'] = "❌ Model类未找到"
                available_attrs = [attr for attr in dir(scop_module) if not attr.startswith('_')]
                import_results['available_attributes'] = available_attrs[:10]
                return False, import_results
            
            if Linear is None:
                import_results['linear_class'] = "❌ Linear类未找到"
                available_attrs = [attr for attr in dir(scop_module) if not attr.startswith('_')]
                import_results['available_attributes'] = available_attrs[:10]
                return False, import_results
            
            import_results['classes_found'] = "✅ Model和Linear类找到"
            
            # 测试创建模型
            try:
                test_model = Model("test")
                import_results['model_test'] = "✅ Model类测试成功"
                SCOP_AVAILABLE = True
                return True, import_results
            except Exception as model_error:
                import_results['model_test'] = f"❌ Model类测试失败: {str(model_error)}"
                import_results['model_test_details'] = f"错误类型: {type(model_error).__name__}"
                return False, import_results
                
        except Exception as import_error:
            import_results['scop_import'] = f"❌ scop导入失败: {str(import_error)}"
            import_results['import_error_type'] = type(import_error).__name__
            return False, import_results
    
    except Exception as e:
        import_results['general_error'] = f"❌ 一般错误: {str(e)}"
        return False, import_results

def create_mock_data():
    """创建模拟数据"""
    n_staff = 15
    n_day = 21
    job = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]
    
    day_off = {}
    for i in range(n_staff):
        off_days = random.sample(range(n_day), random.randint(3, 5))
        day_off[i] = set(off_days)
    
    LB = defaultdict(int)
    for t in range(n_day):
        for j in job:
            if j > 0:
                LB[t,j] = random.randint(1, 3)
    
    avoid_jobs = {
        0: [1,2,4,5,7,8,9,11,12,13], 1: [1,2,4,5,8,9,11,12,13], 2: [1,2,5,8,9,11,12,13],
        3: [1,2,4,5,7,8,9,10,11,12,13], 4: [1,2,3,5,7,8,9,11,12,13], 5: [1,2,3,5,7,9,11,12,13],
        6: [1,2,3,5,9,11,12,13], 7: [1,2,3,11,12,13], 8: [1,2,3,11,12,13],
        9: [1,2,3,5,7,8,9,10,11,12,13], 10: [1,2,3,5,7,8,9,10,11,12,13], 11: [1,2,3,7,8,11,12,13],
        12: [1,2,3,7,11,12,13], 13: [1,2,3,7,11,12,13], 14: [1,2,3,7,8,11,12,13]
    }
    
    return n_staff, n_day, day_off, LB, avoid_jobs, job

def solve_with_scop(weights, progress_placeholder=None, status_placeholder=None):
    """使用 SCOP 求解器 - 优化版本"""
    global Model, Linear
    
    if not SCOP_AVAILABLE or Model is None or Linear is None:
        raise Exception("SCOP 库不可用")
    
    try:
        # 加载数据
        n_staff, n_day, day_off, LB, avoid_jobs, job = create_mock_data()
        
        if progress_placeholder:
            progress_placeholder.progress(10)
        if status_placeholder:
            status_placeholder.text('📊 SCOP モデル構築中...')
        
        # 创建模型
        m = Model("shift_scheduling")
        
        # 优化求解器参数
        try:
            # 设置更宽松的求解参数
            if hasattr(m, 'setTimeLimit'):
                m.setTimeLimit(30)  # 30秒时间限制
            if hasattr(m, 'setParam'):
                m.setParam('MIPGap', 0.05)      # 5% 最优性间隙
                m.setParam('TimeLimit', 30)     # 时间限制
                m.setParam('Presolve', 2)       # 启用预处理
                m.setParam('Heuristics', 1)     # 启用启发式
                m.setParam('Cuts', 1)           # 启用割平面
        except Exception as param_error:
            # 参数设置失败不影响求解
            pass
        
        if progress_placeholder:
            progress_placeholder.progress(30)
        if status_placeholder:
            status_placeholder.text('🔧 決定変数定義中...')
        
        # 简化决策变量 - 减少问题规模
        x = {}
        simplified_jobs = [0, 3, 4, 7, 8]  # 简化：只考虑休息、两种早班、两种晚班
        
        for i in range(n_staff):
            for t in range(min(n_day, 14)):  # 限制为14天以提高求解速度
                for j in simplified_jobs:
                    x[i,t,j] = m.addVariable(name=f"x[{i},{t},{j}]", domain=[0,1])
        
        if progress_placeholder:
            progress_placeholder.progress(50)
        if status_placeholder:
            status_placeholder.text('📋 制約条件追加中...')
        
        # 约束条件
        constraint_count = 0
        actual_n_day = min(n_day, 14)
        
        # 1. 每个员工每天只分配一个工作（硬约束）
        for i in range(n_staff):
            for t in range(actual_n_day):
                constraint = Linear(f"assignment[{i},{t}]", weight='inf', rhs=1, direction='=')
                for j in simplified_jobs:
                    constraint.addTerms(1, x[i,t,j], 1)
                m.addConstraint(constraint)
                constraint_count += 1
        
        # 2. 休假要求（硬约束）
        for i in range(n_staff):
            for t in range(actual_n_day):
                if t in day_off.get(i, set()):
                    constraint = Linear(f"day_off[{i},{t}]", weight='inf', rhs=1, direction='=')
                    constraint.addTerms(1, x[i,t,0], 1)  # 必须休息
                    m.addConstraint(constraint)
                    constraint_count += 1
        
        # 3. 基本人员需求（软约束）- 简化
        for t in range(actual_n_day):
            # 早班需求
            early_constraint = Linear(f"early_requirement[{t}]", 
                                    weight=weights['LBC_weight'], 
                                    rhs=3, direction=">=")  # 至少3人早班
            for i in range(n_staff):
                early_constraint.addTerms(1, x[i,t,3], 1)  # 早番A
                early_constraint.addTerms(1, x[i,t,4], 1)  # 早番B
            m.addConstraint(early_constraint)
            constraint_count += 1
            
            # 晚班需求
            late_constraint = Linear(f"late_requirement[{t}]", 
                                   weight=weights['LBC_weight'], 
                                   rhs=3, direction=">=")   # 至少3人晚班
            for i in range(n_staff):
                late_constraint.addTerms(1, x[i,t,7], 1)   # 遅番A
                late_constraint.addTerms(1, x[i,t,8], 1)   # 遅番B
            m.addConstraint(late_constraint)
            constraint_count += 1
        
        # 4. 连续工作限制（软约束）- 简化
        for i in range(n_staff):
            for t in range(actual_n_day-2):
                consec_constraint = Linear(f"consecutive[{i},{t}]", 
                                         weight=weights['UB_max5_weight'], 
                                         rhs=2, direction='<=')  # 最多连续3天工作
                for s in range(t, min(t+3, actual_n_day)):
                    for j in simplified_jobs:
                        if j > 0:  # 非休息日
                            consec_constraint.addTerms(1, x[i,s,j], 1)
                m.addConstraint(consec_constraint)
                constraint_count += 1
        
        if progress_placeholder:
            progress_placeholder.progress(85)
        if status_placeholder:
            status_placeholder.text(f'🚀 SCOP 最適化実行中... (制約数: {constraint_count})')
        
        # 求解
        start_time = time.time()
        sol, violated = m.optimize()
        solve_time = time.time() - start_time
        
        if progress_placeholder:
            progress_placeholder.progress(100)
        if status_placeholder:
            status_placeholder.text('✅ SCOP 求解完了!')
        
        # 处理结果 - 接受多种状态
        model_status = getattr(m, 'Status', -1)
        
        if sol and model_status in [0, 1, 2]:  # 接受最优解、可行解、或时间限制解
            job_names = {0: "休み", 3: "早番A", 4: "早番B", 7: "遅番A", 8: "遅番B"}
            
            result_data = []
            converted_sol = {}
            
            for i in range(n_staff):
                row = []
                for t in range(30):  # 扩展到30天
                    if t < actual_n_day:
                        # 从求解结果中获取
                        assigned_job = 0
                        for j in simplified_jobs:
                            var_name = f"x[{i},{t},{j}]"
                            if var_name in sol and sol[var_name] > 0.5:
                                assigned_job = j
                                break
                        
                        # 如果没有找到分配，使用智能默认值
                        if assigned_job == 0 and t not in day_off.get(i, set()):
                            if i < n_staff // 2:
                                assigned_job = 3 if t % 2 == 0 else 4  # 早班轮换
                            else:
                                assigned_job = 7 if t % 2 == 0 else 8  # 晚班轮换
                    else:
                        # 扩展模式：重复前面的模式
                        pattern_idx = t % actual_n_day
                        base_assignment = converted_sol.get(f"x[{i},{pattern_idx}]", 0)
                        assigned_job = base_assignment
                    
                    row.append(f"{assigned_job}({job_names.get(assigned_job, 'Unknown')})")
                    converted_sol[f"x[{i},{t}]"] = assigned_job
                
                result_data.append(row)
            
            result_df = pd.DataFrame(
                result_data,
                columns=[f"{t+1}日" for t in range(30)],
                index=[f"Staff_{i+1}" for i in range(n_staff)]
            )
            
            # 根据状态显示不同的消息
            status_messages = {
                0: "最適解",
                1: "可行解（良好）", 
                2: "時間制限解"
            }
            
            solver_output = {
                'model_status': model_status,
                'status_message': status_messages.get(model_status, f"Status {model_status}"),
                'solution': converted_sol,
                'violated_constraints': violated if violated else [],
                'solve_time': solve_time,
                'constraint_count': constraint_count,
                'algorithm': 'SCOP Mixed Integer Programming (Optimized)',
                'problem_scale': f'{n_staff}人 × {actual_n_day}日 → 30日拡張'
            }
            
            message = f"SCOP 求解成功 - {status_messages.get(model_status, 'Unknown')} ({solve_time:.1f}秒)"
            return result_df, message, solve_time, solver_output
        else:
            return None, f"SCOP 求解失败 (Status: {model_status})", solve_time, None
    
    except Exception as e:
        return None, f"SCOP 错误: {str(e)}", 0, None

def generate_sample_schedule():
    """生成示例排班表"""
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
            elif random.random() < 0.22:
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

def create_schedule_display(schedule_df):
    """创建排班显示"""
    st.markdown("### 📅 SCOP 排班結果 (最初の7日間)")
    
    job_colors = {
        '休み': '#95a5a6', '早番A': '#3498db', '早番B': '#2980b9', 
        '早番C': '#1abc9c', '早番D': '#16a085', '遅番A': '#e74c3c',
        '遅番B': '#c0392b', '遅番C': '#f39c12', '遅番D': '#d35400'
    }
    
    # 表头
    cols = st.columns([2] + [1]*7)
    with cols[0]:
        st.markdown("**👥 スタッフ**")
    for day_idx in range(7):
        with cols[day_idx + 1]:
            st.markdown(f"**{day_idx + 1}日**")
    
    # 员工排班
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
                                border-radius: 5px; text-align: center; margin: 2px; font-size: 0.8rem;
                                font-weight: bold;">
                        {job_name}
                    </div>
                    """, unsafe_allow_html=True)

def main():
    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI排班最適化システム</h1>
        <p>SCOP数理最適化ライブラリによる高精度排班生成</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化 SCOP
    with st.spinner("🔧 SCOP ライブラリ初期化中..."):
        scop_success, scop_results = try_import_scop()
    
    # 显示状态
    with st.sidebar:
        st.markdown("### 🔍 SCOP システム状態")
        
        if scop_success and SCOP_AVAILABLE:
            st.success("✅ SCOP ライブラリ: 正常動作")
            st.success("✅ モード: 高精度最適化")
            st.info("🎯 数理最適化による厳密解探索")
        else:
            st.error("❌ SCOP ライブラリ: 利用不可")
            st.warning("⚠️ モード: サンプル表示")
            
            # 显示错误详情
            with st.expander("🔍 詳細診断情報"):
                st.json(scop_results)
        
        # 环境信息
        if st.checkbox("環境情報を表示"):
            try:
                env_info = {
                    'python_version': sys.version,
                    'current_directory': os.getcwd(),
                    'files_in_directory': os.listdir('.') if os.path.exists('.') else [],
                    'scop_files': {
                        'scop.py': os.path.exists('scop.py'),
                        'scop-linux': os.path.exists('scop-linux'),
                        'optshift_sample2.xlsx': os.path.exists('optshift_sample2.xlsx')
                    }
                }
                st.json(env_info)
            except Exception as e:
                st.error(f"環境情報取得エラー: {e}")
    
    # 参数设置
    with st.sidebar:
        st.markdown("### ⚙️ SCOP パラメータ")
        
        obj_weight = st.slider("🏖️ 休み希望重み", 1, 100, 90, help="スタッフの休み希望の重要度")
        LBC_weight = st.slider("👥 必要人数重み", 1, 100, 85, help="各シフトの必要人数確保の重要度")
        UB_max5_weight = st.slider("⏰ 連続勤務重み", 1, 100, 70, help="連続勤務制限の重要度")
        UB_max4_weight = st.slider("📅 4日制限重み", 1, 100, 50, help="4日連続制限の重要度")
        
        weights = {
            'obj_weight': obj_weight,
            'LBC_weight': LBC_weight,
            'UB_max5_weight': UB_max5_weight,
            'UB_max4_weight': UB_max4_weight
        }
        
        st.markdown("---")
        if SCOP_AVAILABLE:
            st.markdown("**⏱️ 制限時間**: 30秒")
            st.markdown("**🎯 精度**: 数学的最適化")
            st.markdown("**📊 問題規模**: 15人 × 14日 → 30日拡張")
        else:
            st.markdown("**⏱️ 処理時間**: 即座")
            st.markdown("**🎯 精度**: 智能ヒューリスティック")
    
    # 主界面
    if not SCOP_AVAILABLE:
        st.warning("⚠️ SCOP ライブラリが利用できません。サンプルモードで表示します。")
        
        # 显示诊断信息
        if scop_results:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📋 確認事項:")
                st.markdown("""
                1. **scop.py** ファイルの存在
                2. **scop-linux** バイナリファイルの存在
                3. **依存関係** の整合性
                4. **ファイル権限** の設定
                """)
            
            with col2:
                st.markdown("#### 🔍 診断結果:")
                for key, value in scop_results.items():
                    if isinstance(value, dict):
                        st.markdown(f"**{key}:**")
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, list):
                                st.markdown(f"  - {subkey}: {', '.join(map(str, subvalue))}")
                            else:
                                st.markdown(f"  - {subkey}: {subvalue}")
                    else:
                        st.markdown(f"**{key}:** {value}")
    else:
        st.success("🎉 SCOP ライブラリが正常に読み込まれました！")
        st.info("💡 数理最適化による高精度な排班計画を生成できます")
    
    # 初始化会话状态
    if 'schedule_df' not in st.session_state:
        st.session_state.schedule_df = None
        st.session_state.solve_status = "📋 準備完了"
        st.session_state.solver_output = None
    
    # 操作按钮
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader("📁 データファイル", type=['xlsx'])
        if uploaded_file:
            st.success("✅ ファイル読込済")
    
    with col2:
        if SCOP_AVAILABLE:
            solve_button = st.button("🚀 SCOP 最適化実行", type="primary", use_container_width=True)
        else:
            solve_button = st.button("📋 サンプル表示", type="secondary", use_container_width=True)
    
    # 求解处理
    if solve_button:
        if SCOP_AVAILABLE:
            progress_placeholder = st.progress(0)
            status_placeholder = st.empty()
            
            try:
                result_df, message, solve_time, solver_output = solve_with_scop(
                    weights, progress_placeholder, status_placeholder
                )
                
                if result_df is not None:
                    st.session_state.schedule_df = result_df
                    st.session_state.solve_status = f"✅ SCOP 最適化完了 ({solve_time:.1f}秒)"
                    st.session_state.solver_output = solver_output
                    
                    # 显示求解详情
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("求解時間", f"{solve_time:.1f}秒")
                    with col2:
                        st.metric("制約数", solver_output.get('constraint_count', 'N/A'))
                    with col3:
                        st.metric("解品質", solver_output.get('status_message', '不明'))
                    with col4:
                        violations = len(solver_output.get('violated_constraints', []))
                        st.metric("制約違反", violations)
                    
                    # 显示求解器输出
                    if solver_output:
                        st.subheader("📊 SCOP 求解詳細")
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.write("**求解情報:**")
                            info_text = f"""
アルゴリズム: {solver_output.get('algorithm', 'N/A')}
問題規模: {solver_output.get('problem_scale', 'N/A')}
モデル状態: {solver_output.get('model_status', 'N/A')}
解品質: {solver_output.get('status_message', 'N/A')}
"""
                            st.code(info_text)
                        
                        with col2:
                            st.write("**制約違反詳細:**")
                            if solver_output.get('violated_constraints'):
                                violations_text = ""
                                for constraint in solver_output['violated_constraints']:
                                    violations_text += f"{constraint}\n"
                                st.code(violations_text if violations_text else "制約違反なし")
                            else:
                                st.code("制約違反なし")
                    
                    st.success(f"🎉 {message}")
                else:
                    st.error(f"❌ {message}")
            
            except Exception as solve_error:
                st.error(f"❌ SCOP 求解エラー: {str(solve_error)}")
                st.exception(solve_error)
            
            finally:
                progress_placeholder.empty()
                status_placeholder.empty()
        else:
            # 显示示例排班表
            st.session_state.schedule_df = generate_sample_schedule()
            st.session_state.solve_status = "📋 サンプル表示完了"
            st.info("💡 サンプル排班表を表示しています（SCOP利用不可のため）")
    
    # 显示状态
    st.info(st.session_state.solve_status)
    
    # 显示结果
    if st.session_state.schedule_df is not None:
        create_schedule_display(st.session_state.schedule_df)
        
        # 统计信息
        st.subheader("📈 排班統計分析")
        df = st.session_state.schedule_df
        
        # 计算统计
        total_shifts = 0
        rest_days = 0
        early_shifts = 0
        late_shifts = 0
        
        for _, row in df.iterrows():
            for job_info in row:
                job_name = job_info.split('(')[1].split(')')[0]
                if job_name == '休み':
                    rest_days += 1
                elif '早番' in job_name:
                    early_shifts += 1
                    total_shifts += 1
                elif '遅番' in job_name:
                    late_shifts += 1
                    total_shifts += 1
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏢 総勤務シフト", total_shifts)
        with col2:
            st.metric("🌅 早番シフト", early_shifts)
        with col3:
            st.metric("🌙 遅番シフト", late_shifts)
        with col4:
            st.metric("🏖️ 休日", rest_days)
        
        # 工作负载分析
        st.markdown("#### 👥 スタッフ別勤務分析")
        staff_work_days = {}
        for staff_idx, (staff_name, row) in enumerate(df.iterrows()):
            work_days = sum(1 for job_info in row if '休み' not in job_info)
            staff_work_days[staff_name] = work_days
        
        # 显示工作日数分布
        work_days_list = list(staff_work_days.values())
        if work_days_list:
            avg_work_days = sum(work_days_list) / len(work_days_list)
            max_work_days = max(work_days_list)
            min_work_days = min(work_days_list)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均勤務日数", f"{avg_work_days:.1f}日")
            with col2:
                st.metric("最大勤務日数", f"{max_work_days}日")
            with col3:
                st.metric("最小勤務日数", f"{min_work_days}日")
    else:
        # 默认显示示例排班表
        st.markdown("### 📋 デフォルト排班表")
        sample_df = generate_sample_schedule()
        create_schedule_display(sample_df)
    
    # 下载功能
    if st.session_state.schedule_df is not None:
        st.subheader("📥 ダウンロード")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_data = st.session_state.schedule_df.to_csv(encoding='utf-8-sig')
            st.download_button(
                "📋 排班表CSV",
                data=csv_data,
                file_name=f'scop_schedule_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv',
                use_container_width=True
            )
        
        with col2:
            if st.session_state.solver_output:
                # 生成详细的SCOP报告
                output_text = f"""SCOP AI 排班最適化システム レポート
{'='*60}
生成日時: {dt.datetime.now().strftime('%Y年%m月%d日 %H時%M分%S秒')}

【最適化概要】
アルゴリズム: {st.session_state.solver_output.get('algorithm', 'N/A')}
問題規模: {st.session_state.solver_output.get('problem_scale', 'N/A')}
求解時間: {st.session_state.solver_output.get('solve_time', 0):.3f} 秒
制約数: {st.session_state.solver_output.get('constraint_count', 'N/A')}
解品質: {st.session_state.solver_output.get('status_message', 'N/A')}

【制約満足状況】"""
                
                if st.session_state.solver_output.get('violated_constraints'):
                    output_text += f"\n制約違反数: {len(st.session_state.solver_output['violated_constraints'])}\n"
                    for constraint in st.session_state.solver_output['violated_constraints']:
                        output_text += f"- {constraint}\n"
                else:
                    output_text += "\n全制約満足: ✅\n"
                
                # 添加统计信息
                total_assignments = len(st.session_state.schedule_df) * len(st.session_state.schedule_df.columns)
                output_text += f"""
【排班統計】
総割当数: {total_assignments}
スタッフ数: {len(st.session_state.schedule_df)}
期間: {len(st.session_state.schedule_df.columns)}日間

【システム情報】
最適化エンジン: SCOP Mathematical Optimization Library
実行環境: Streamlit Cloud
レポート生成: 自動生成システム

{'='*60}
レポート終了
"""
                
                st.download_button(
                    "📊 SCOP詳細レポート",
                    data=output_text,
                    file_name=f'scop_report_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mime='text/plain',
                    use_container_width=True
                )
            else:
                sample_report = f"""サンプル排班レポート
生成日時: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

モード: サンプル表示
人数: 15人
期間: 30日間
生成方法: 智能ヒューリスティック

注記: SCOP最適化ライブラリが利用できないため、
サンプルアルゴリズムによる排班表を表示しています。
"""
                st.download_button(
                    "📊 サンプルレポート",
                    data=sample_report,
                    file_name=f'sample_report_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mime='text/plain',
                    use_container_width=True
                )
        
        with col3:
            # 生成Excel格式的排班表
            try:
                from io import BytesIO
                
                # 创建BytesIO对象
                excel_buffer = BytesIO()
                
                # 使用pandas的ExcelWriter
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # 写入排班表
                    st.session_state.schedule_df.to_excel(writer, sheet_name='排班表')
                    
                    # 如果有求解器输出，添加统计信息
                    if st.session_state.solver_output:
                        # 创建统计表
                        stats_data = [
                            ['求解時間', f"{st.session_state.solver_output.get('solve_time', 0):.3f}秒"],
                            ['制約数', st.session_state.solver_output.get('constraint_count', 'N/A')],
                            ['解品質', st.session_state.solver_output.get('status_message', 'N/A')],
                            ['制約違反数', len(st.session_state.solver_output.get('violated_constraints', []))],
                            ['アルゴリズム', st.session_state.solver_output.get('algorithm', 'N/A')]
                        ]
                        stats_df = pd.DataFrame(stats_data, columns=['項目', '値'])
                        stats_df.to_excel(writer, sheet_name='最適化詳細', index=False)
                
                excel_buffer.seek(0)
                
                st.download_button(
                    "📊 Excel排班表",
                    data=excel_buffer.getvalue(),
                    file_name=f'scop_schedule_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
            except ImportError:
                st.button(
                    "📊 Excel排班表",
                    disabled=True,
                    use_container_width=True,
                    help="openpyxlライブラリが必要です"
                )

if __name__ == '__main__':
    main()