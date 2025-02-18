import pandas as pd
import streamlit as st
from io import BytesIO
import plotly.express as px
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    format='%(asctime)s - %(message)s',
    level=logging.INFO
)

def log_action(action):
    user = st.session_state.get('user', 'unknown')
    logging.info(f"User: {user} - {action}")

# Конфигурация
DAYS_IN_MONTH = 28
NORM_HOURS = 160
WORK_GROUPS = ['ГР1', 'ГР2', 'ГР3', 'ГР4', 'офис']

# Шаблоны графиков
SCHEDULE_TEMPLATES = {
    'График1': [11.5, 11.5, "", 11.5, 11.5, "", "", "", 11.5, 11.5],
    'График2': [11.5, 7.5, "", "", 11.5, 11.5, "", 11.5, 11.5],
    'График3': ["", 11.5, 11.5, "", "", "", 11.5, 11.5],
    'График4': ["", "", 11.5, 11.5, "", 11.5, 11.5],
    'Офис': [8, 8, 8, 8, 8]
}

class EmployeeSchedule:
    def __init__(self, name, group, schedule_type, exceptions=None, absences=None):
        self.name = name
        self.group = group
        self.schedule_type = schedule_type
        self.exceptions = exceptions or {}
        self.absences = absences or {}

    def generate_schedule(self):
        base_pattern = SCHEDULE_TEMPLATES[self.schedule_type]
        schedule = {}
        
        pattern_index = 0
        for day in range(1, DAYS_IN_MONTH+1):
            day_str = str(day)
            if day_str in self.exceptions:
                schedule[day_str] = self.exceptions[day_str]
            elif day_str in self.absences:
                schedule[day_str] = self.absences[day_str]
            else:
                schedule[day_str] = base_pattern[pattern_index % len(base_pattern)]
                pattern_index += 1
        
        total = sum(
            float(h) if isinstance(h, (int, float, str)) and str(h).replace('.', '').isdigit() 
            else 0 
            for h in schedule.values()
        )
        
        return {
            'Ф.И.О. мастера смены': self.name,
            'ГР №': self.group,
            **schedule,
            'Факт ФРВ': round(total, 1),
            'от ФРВ': round(total - NORM_HOURS, 1)
        }

def create_schedule():
    employees = [
        EmployeeSchedule("Феоктистова Е.А.", "ГР1", "График1", {'12': "ГО", '27': '4'}),
        EmployeeSchedule("Третьяков А.И.", "ГР1", "График1"),
        EmployeeSchedule("Грачева Т.В.", "ГР1", "График1"),
        EmployeeSchedule("Белоусов А.В.", "ГР1", "График1", {'12': "ГО"}),
        EmployeeSchedule("Давыдова С.В.", "ГР1", "График1"),
        EmployeeSchedule("Саранцев А.Н. ученик", "ГР1", "График1", {'6': "ув"}),
        EmployeeSchedule("Панфилов А.В.", "ГР2", "График2", {'22': "го"}),
        EmployeeSchedule("Свиридов А.О. (стажер)", "ГР2", "График2"),
        EmployeeSchedule("Смирнов Н.Н.", "ГР2", "График2"),
        EmployeeSchedule("Синякина С.А.", "ГР2", "График2"),
        EmployeeSchedule("Пантюхин А.Д.", "ГР2", "График2", {'23': "го"}),
        EmployeeSchedule("Давыдова О.И.", "ГР2", "График2"),
        EmployeeSchedule("Роменский Р.С.", "ГР2", "График2"),
        EmployeeSchedule("Лукашенкова С.В.", "ГР3", "График3"),
        EmployeeSchedule("Раку О.А.", "ГР3", "График3", {'8': "б/л"}),
        EmployeeSchedule("Михеева А.В.", "ГР3", "График3", {'15': "ГО"}),
        EmployeeSchedule("Антипенко В.Н.", "ГР3", "График3"),
        EmployeeSchedule("Юдина И.Е.", "ГР4", "График4"),
        EmployeeSchedule("Лисовская Т.А.", "ГР4", "График4", {'4': "б/л"}),
        EmployeeSchedule("Галкина В.А.", "ГР4", "График4", {'11': "б/л"}),
        EmployeeSchedule("Незбудеев Д.С.", "ГР4", "График4"),
        EmployeeSchedule("Смоляков А.А.", "ГР4", "График4", {'12': "ГО"}),
        EmployeeSchedule("Долгоаршиннных Т.Р.", "ГР4", "График4"),
        EmployeeSchedule("Подгорбунский Д.А.", "офис", "Офис")
    ]
    
    return pd.DataFrame([e.generate_schedule() for e in employees])

def validate_data(df):
    errors = []
    valid_marks = ['', 'ГО', 'б/л', 'ув', 'го']
    for idx, row in df.iterrows():
        for day in range(1, DAYS_IN_MONTH+1):
            value = row[str(day)]
            # Исправленное условие:
            if not (isinstance(value, (int, float)) and (str(value) not in valid_marks):
                errors.append(f"Ошибка: {row['Ф.И.О. мастера смены']} день {day} - некорректное значение '{value}'")
    return errors

def edit_data(df):
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Ф.И.О. мастера смены": st.column_config.TextColumn(required=True),
            "ГР №": st.column_config.SelectboxColumn(options=WORK_GROUPS)
        },
        key="data_editor"
    )
    if not df.equals(edited_df):
        log_action("Данные изменены через редактор")
    return edited_df

def main():
    st.set_page_config(layout="wide", page_title="График работы цеха", page_icon="📅")
    
    # Инициализация данных
    if 'schedule_data' not in st.session_state:
        st.session_state.schedule_data = create_schedule()
    
    # Боковая панель
    st.sidebar.header("Управление")
    
    # Поиск
    search_query = st.sidebar.text_input("Поиск сотрудника")
    
    # Сортировка
    sort_col = st.sidebar.selectbox("Сортировать по", st.session_state.schedule_data.columns)
    sort_order = st.sidebar.radio("Порядок сортировки", ["По возрастанию", "По убыванию"])
    
    # Фильтрация
    selected_groups = st.sidebar.multiselect("Фильтр по группам", WORK_GROUPS)
    show_overtime = st.sidebar.checkbox("Показать только переработки")
    
    # Применение фильтров
    filtered_df = st.session_state.schedule_data
    if search_query:
        filtered_df = filtered_df[filtered_df['Ф.И.О. мастера смены'].str.contains(search_query, case=False)]
    if selected_groups:
        filtered_df = filtered_df[filtered_df['ГР №'].isin(selected_groups)]
    if show_overtime:
        filtered_df = filtered_df[filtered_df['от ФРВ'] > 0]
    
    # Сортировка
    filtered_df = filtered_df.sort_values(
        by=sort_col, 
        ascending=sort_order == "По возрастанию"
    )
    
    # Основной интерфейс
    st.title("📅 Управление графиком работы цеха МиЖ ГЛФ")
    
    # Редактирование данных
    st.header("Табель учета рабочего времени")
    edited_df = edit_data(filtered_df)
    
    # Валидация
    errors = validate_data(edited_df)
    if errors:
        st.error("Обнаружены ошибки в данных:")
        for error in errors:
            st.write(f"⚠️ {error}")
    
    # Визуализация
    st.header("Аналитика")
    
    tab1, tab2 = st.tabs(["Распределение часов", "Статистика по группам"])
    
    with tab1:
        fig1 = px.histogram(
            edited_df, 
            x='Факт ФРВ',
            title='Распределение отработанных часов',
            nbins=20
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        group_stats = edited_df['ГР №'].value_counts().reset_index()
        fig2 = px.pie(
            group_stats, 
            values='count',
            names='ГР №',
            title='Распределение сотрудников по группам'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Статистика
    st.subheader("Ключевые показатели")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего сотрудников", len(edited_df))
    with col2:
        avg_hours = edited_df['Факт ФРВ'].mean()
        st.metric("Среднее время", f"{avg_hours:.1f} ч")
    with col3:
        overtime_count = len(edited_df[edited_df['от ФРВ'] > 0])
        st.metric("С переработкой", f"{overtime_count} чел")
    
    # Экспорт
    st.sidebar.header("Экспорт данных")
    export_format = st.sidebar.selectbox("Формат экспорта", ["Excel", "CSV"])
    
    if st.sidebar.button("Экспортировать данные"):
        output = BytesIO()
        if export_format == "Excel":
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_ext = "xlsx"
        else:
            output.write(edited_df.to_csv(index=False).encode('utf-8'))
            mime_type = "text/csv"
            file_ext = "csv"
        
        st.sidebar.download_button(
            label=f"Скачать {export_format}",
            data=output.getvalue(),
            file_name=f"график_работы_{datetime.now().strftime('%Y%m%d')}.{file_ext}",
            mime=mime_type
        )
        log_action(f"Экспорт данных в формате {export_format}")

if __name__ == "__main__":
    main()