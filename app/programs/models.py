from datetime import datetime, date

import requests
from app.main.func import (
    plan_curriculum_disciplines,
    db_filter_req,
    get_active_staff_id,
    get_data, get_system_user_name,
)
from app.plans.func import create_wp
from app.programs.func import plan_department_disciplines
from config import ApeksAPI


class ApeksDeptData:
    def __init__(self):
        self.active_staff_id = get_active_staff_id()
        self.data = get_data(self.active_staff_id)
        self.departments = self.data["departments"]


class WorkProgram:
    def __init__(self, curriculum_discipline_id):
        self.curriculum_discipline_id = curriculum_discipline_id
        self.mm_work_programs = db_filter_req(
            "mm_work_programs", "curriculum_discipline_id", curriculum_discipline_id
        )
        self.work_program_id = self.mm_work_programs[0]["id"]
        self.name = self.mm_work_programs[0]["name"]
        self.mm_work_programs_items = {
            "name": "name",  # Название программы
            "reviewers_ext": "reviewers_ext",  # Рецензенты
            "date_approval": "date_approval",
            "date_methodical": "date_methodical",
            "document_methodical": "document_methodical",
            "date_academic": "date_academic",
            "document_academic": "document_academic",
            "status": "status",
        }
        self.special = {
            "date_department": "date_department",  # Дата заседания кафедры
            "document_department": "document_department",  # Протокол заседания кафедры
        }
        self.mm_sections_items = {
            "purposes": "purposes",  # Цели дисциплины
            "tasks": "tasks",  # Задачи дисциплины
            "place_in_structure": "place_in_structure",  # Место в структуре ООП
        }
        self.mm_work_programs_data_items = {
            "authorprint": 29,  # Автор(ы) рабочей программы (для печати)
            "no_next_disc": 30,  # Пояснение к таблице с последующими дисциплинами (информация об отсутствии)
            "templan_info": 31,  # Примечание к тематическому плану
            "self_provision": 8,  # Обеспечение самостоятельной работы
            "test_criteria": 32,  # Критерии оценки для сдачи промежуточной аттестации в форме тестирования
            "course_works": 12,  # Тематика курсовых работ
            "practice": 10,  # Практикум
            "control_works": 13,  # Тематика контрольных работ
            "exam_form_desc": 33,  # Примерные оценочные средства для проведения промежуточной аттестации
            "task_works": 9,  # Задачи
            "tests": 19,  # Тесты
            "regulations": 16,  # Нормативные акты
            "library_main": 1,  # Основная литература
            "library_add": 2,  # Дополнительная литература
            "library_np": 3,  # Научная продукция
            "internet": 18,  # Ресурсы информационно-телекоммуникационной сети Интернет
            "software": 15,  # Программное обеспечение
            "ref_system": 17,  # Базы данных, информационно-справочные и поисковые системы
            "materials_base": 20,  # Описание материально-технической базы
        }

    def get(self, parameter):
        """Get work program field data"""
        if parameter in self.mm_work_programs_items:
            return self.mm_work_programs[0][self.mm_work_programs_items.get(parameter)]
        elif parameter in self.special:
            date_department = self.mm_work_programs[-1]["date_department"]
            document_department = self.mm_work_programs[-1]["document_department"]
            if date_department:
                d = date_department.split("-")
                date_department = f"{d[-1]}.{d[-2]}.{d[-3]}"
            else:
                date_department = "[Не заполнена]"
            if document_department is None:
                document_department = "[Отсутствует]"
            return f"Дата заседания кафедры: {date_department}\r\nПротокол № {document_department}"
        elif parameter in self.mm_sections_items:
            try:
                data = db_filter_req(
                    "mm_sections", "work_program_id", self.work_program_id
                )[-1][self.mm_sections_items.get(parameter)]
                return data
            except IndexError:
                params = {"token": ApeksAPI.TOKEN}
                data = {
                    "table": "mm_sections",
                    "fields[work_program_id]": self.work_program_id,
                }
                requests.post(
                    ApeksAPI.URL + "/api/call/system-database/add",
                    params=params,
                    data=data,
                )
                return ""
        elif parameter in self.mm_work_programs_data_items:
            try:
                params = {
                    "token": ApeksAPI.TOKEN,
                    "table": "mm_work_programs_data",
                    "filter[work_program_id]": self.work_program_id,
                    "filter[field_id]": str(
                        self.mm_work_programs_data_items.get(parameter)
                    ),
                }
                return requests.get(
                    ApeksAPI.URL + "/api/call/system-database/get", params=params
                ).json()["data"][-1]["data"]
            except IndexError:
                return ""
        else:
            return "Wrong parameter"

    def edit(self, parameter, load_data):
        """Edit work program field data"""
        def mm_work_programs_items(f_param, f_data):
            params = {"token": ApeksAPI.TOKEN}
            data = {
                "table": "mm_work_programs",
                "filter[id]": self.work_program_id,
                "fields[" + f_param + "]": str(f_data),
            }
            requests.post(
                ApeksAPI.URL + "/api/call/system-database/edit",
                params=params,
                data=data,
            )
        if parameter in self.mm_work_programs_items:
            mm_work_programs_items(parameter, load_data)
            self.mm_work_programs = db_filter_req(
                "mm_work_programs",
                "curriculum_discipline_id",
                self.curriculum_discipline_id,
            )
        elif parameter in self.special:
            param = 'date_department'
            d = load_data.split("\r\n")[0].replace("Дата заседания кафедры:", "").replace(" ", "")
            d = datetime.strptime(d, '%d.%m.%Y')
            data = date.isoformat(d)
            mm_work_programs_items(param, data)

            param = 'document_department'
            data = load_data.split("\r\n")[1].replace("Протокол №", "").replace(" ", "")
            mm_work_programs_items(param, data)

            self.mm_work_programs = db_filter_req(
                "mm_work_programs",
                "curriculum_discipline_id",
                self.curriculum_discipline_id,
            )
        elif parameter in self.mm_sections_items:
            params = {"token": ApeksAPI.TOKEN}
            data = {
                "table": "mm_sections",
                "filter[work_program_id]": self.work_program_id,
                "fields[" + self.mm_sections_items.get(parameter) + "]": str(load_data),
            }
            r = requests.post(
                ApeksAPI.URL + "/api/call/system-database/edit",
                params=params,
                data=data,
            )
            return r.json()
        elif parameter in self.mm_work_programs_data_items:
            params = {"token": ApeksAPI.TOKEN}
            data = {
                "table": "mm_work_programs_data",
                "filter[work_program_id]": self.work_program_id,
                "filter[field_id]": self.mm_work_programs_data_items.get(parameter),
                "fields[data]": str(load_data),
            }
            r = requests.post(
                ApeksAPI.URL + "/api/call/system-database/edit",
                params=params,
                data=data,
            )
            return r.json()
        else:
            return "Wrong parameter"

    def get_signs(self):
        """Получение информации о согласовании программы"""
        signs_data = db_filter_req(
            'mm_work_programs_signs',
            'work_program_id',
            self.work_program_id
        )
        signs = []
        if signs_data:
            for sign in signs_data:
                signs.append(f'{get_system_user_name(sign["user_id"])} ({sign["timestamp"]})')
        else:
            signs.append("Не согласована")
        return signs

    def wp_status_change(self, status):
        """Статус утверждения программы (status = 1-утв, 2-неутв)"""
        params = {"token": ApeksAPI.TOKEN}
        data = {
            "table": "mm_work_programs",
            "filter[id]": self.work_program_id,
            "fields[status]": str(status),
        }
        requests.post(ApeksAPI.URL + "/api/call/system-database/edit",
                      params=params, data=data)


class WorkProgramProcessing:
    def __init__(self, curriculum_discipline_id):
        self.curriculum_discipline_id = curriculum_discipline_id
        self.wp_data = self.wp_data_get()
        if not self.wp_data:
            create_wp(self.curriculum_discipline_id)
            self.wp_data = self.wp_data_get()
        self.control_data = self.control_data()
        self.comp_level = self.comp_level_get()
        if not self.comp_level:
            self.comp_level_add()
            self.comp_level = self.comp_level_get()

    def wp_data_get(self):
        return db_filter_req(
            "mm_work_programs", "curriculum_discipline_id", self.curriculum_discipline_id
        )

    def control_data(self):
        """Получение последней формы контроля и семестра дисциплины"""
        control_type_id = {1: [], 2: [], 6: [],
                           14: []}  # 1: ["зкзамен"], 2: ["Зачет"], 6: ["Зачет с оценкой"], 14: ["Итоговая аттестация"]
        apeks_data = db_filter_req(
            "plan_control_works", "curriculum_discipline_id", self.curriculum_discipline_id
        )
        for data in apeks_data:
            if int(data['control_type_id']) in list(control_type_id.keys()):
                control_type_id[int(data.get('control_type_id'))].append(int(data.get('semester_id')))
        for control in control_type_id:
            if control_type_id[control]:
                semester = sorted(control_type_id[control])[-1]
                return control, semester
            else:
                return None

    def comp_level_get(self):
        return db_filter_req(
            "mm_competency_levels", "work_program_id", self.wp_data[0]["id"]
        )

    def comp_level_add(self):
        """Создание уровня сформированности компетенций (последний семестр [-1])"""
        if self.control_data:
            params = {"token": ApeksAPI.TOKEN}
            data = {
                "table": "mm_competency_levels",
                "fields[work_program_id]": self.wp_data[0]["id"],
                "fields[control_type_id]": self.control_data[0],
                "fields[semester_id]": self.control_data[1],
                "fields[level]": "1",
            }
            requests.post(
                ApeksAPI.URL + "/api/call/system-database/add", params=params, data=data
            )
            return "Уровень создан"
        else:
            return "Не заполнен план"

    def comp_level_edit(self, knowledge, abilities, ownerships):
        """Редактирование индикаторов в таблице Уровни сформированности"""
        if len(self.comp_level) > 1:  # Удаляем уровни если больше 1
            for i in self.comp_level:
                if i["level"] != "1":
                    params = {
                        "token": ApeksAPI.TOKEN,
                        "table": "mm_competency_levels",
                        "filter[work_program_id]": self.wp_data[0]["id"],
                        "filter[level]": i["level"],
                    }
                    requests.delete(
                        ApeksAPI.URL + "/api/call/system-database/delete", params=params
                    )

        if self.control_data:
            """Проверка заполненности плана т.к. нужен семестр, выбор последнего семестка и формы контроля"""
            params = {"token": ApeksAPI.TOKEN}
            data = {
                "table": "mm_competency_levels",
                "filter[work_program_id]": self.wp_data[0]["id"],
                "filter[level]": "1",
                "fields[semester_id]": self.control_data[1],
                "fields[control_type_id]": self.control_data[0],
                "fields[knowledge]": knowledge,
                "fields[abilities]": abilities,
                "fields[ownerships]": ownerships,
            }
            requests.post(
                ApeksAPI.URL + "/api/call/system-database/edit",
                params=params,
                data=data,
            )

    def comp_data_get(self):
        """Получение данных о заполненных данных компетенций"""
        return db_filter_req(
            "mm_work_programs_competencies_data",
            "work_program_id",
            self.wp_data[0]["id"],
        )

    def comp_data_add(self, competency_id, field_id, value):
        """Загрузка данных компетенции (field_id 1-знать, 2-уметь, 3-владеть)"""
        params = {"token": ApeksAPI.TOKEN}
        data = {
            "table": "mm_work_programs_competencies_data",
            "fields[work_program_id]": self.wp_data[0]["id"],
            "fields[competency_id]": competency_id,
            "fields[field_id]": field_id,
            "fields[value]": value,
        }
        requests.post(
            ApeksAPI.URL + "/api/call/system-database/add", params=params, data=data
        )

    #     def comp_data_edit(self, competency_id, field_id, value): # Редактирование заполненных данных
    #         data = {'token': ApeksAPI.TOKEN,
    #                 'table': 'mm_work_programs_competencies_data',
    #                 'filter[work_program_id]': self.wp_data[0]['id'],
    #                 'filter[competency_id]': competency_id,
    #                 'filter[field_id]': field_id,
    #                 'fields[value]': value,}
    #         requests.post(ApeksAPI.URL + '/api/call/system-database/edit', data=data)
    #         self.comp_data = self.comp_data_get()

    def comp_data_del(self):
        """Удаление содержания компетенций"""
        params = {
            "token": ApeksAPI.TOKEN,
            "table": "mm_work_programs_competencies_data",
            "filter[work_program_id]": self.wp_data[0]["id"],
        }
        requests.delete(
            ApeksAPI.URL + "/api/call/system-database/delete", params=params
        )


class WorkProgramBunchData:
    def __init__(self, education_plan_id, parameter):
        self.parameter = parameter
        self.education_plan_id = education_plan_id

    def all(self):
        disc_list = plan_curriculum_disciplines(self.education_plan_id)
        return self.wp_list_processing(disc_list)

    def department(self, department_id):
        disc_list = plan_department_disciplines(self.education_plan_id, department_id)
        return self.wp_list_processing(disc_list)

    def wp_list_processing(self, disc_list):
        result = {}
        for disc in disc_list:
            try:
                wp = WorkProgram(disc)
                try:
                    result[" ".join(disc_list[disc])] = [wp.get(self.parameter), disc]
                except IndexError:
                    result[" ".join(disc_list[disc])] = ["", disc]
            except IndexError:
                result[" ".join(disc_list[disc])] = ["-->Программа отсутствует<--", disc]
        return result
