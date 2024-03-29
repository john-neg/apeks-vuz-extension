import operator
import os

from flask import flash, redirect, render_template, request, url_for
from flask.views import View
from flask_login import login_required

from config import ApeksConfig, FlaskConfig, PermissionsConfig
from . import bp
from .forms import LibraryForm
from .func import library_file_processing
from ..auth.func import permission_required
from ..core.classes.EducationPlan import EducationPlan, EducationPlanWorkPrograms
from ..core.forms import ChoosePlan
from ..core.func.api_get import api_get_db_table, check_api_db_response
from ..core.func.app_core import allowed_file
from ..core.func.education_plan import (
    get_education_plans,
    get_plan_curriculum_disciplines,
    get_plan_education_specialties,
)
from ..core.func.work_program import (
    get_work_programs_data,
    load_lib_add_field,
    load_lib_edit_field,
)
from ..core.reports.library_report import library_report

load_sources_permission_required = permission_required(
    PermissionsConfig.LIBRARY_LOAD_SOURCES_PERMISSION
)
load_internet_links_permission_required = permission_required(
    PermissionsConfig.LIBRARY_LOAD_INTERNET_LINKS_PERMISSION
)
load_info_systems_permission_required = permission_required(
    PermissionsConfig.LIBRARY_LOAD_INFO_SYSTEMS_PERMISSION
)
load_science_products_permission_required = permission_required(
    PermissionsConfig.LIBRARY_LOAD_SCIENCE_PRODUCTS_PERMISSION
)


class LibraryChoosePlanView(View):
    methods = ["GET", "POST"]

    def __init__(self, lib_type, title, lib_type_name):
        self.template_name = "library/choose_plan.html"
        self.lib_type = lib_type
        self.lib_type_name = lib_type_name
        self.title = title

    @login_required
    async def dispatch_request(self):
        form = ChoosePlan()
        specialities = await get_plan_education_specialties()
        form.edu_spec.choices = list(specialities.items())
        if request.method == "POST":
            edu_spec = request.form.get("edu_spec")
            plans = await get_education_plans(edu_spec)
            form.edu_plan.choices = list(
                sorted(plans.items(), key=operator.itemgetter(1), reverse=True)
            )
            if request.form.get("edu_plan") and form.validate_on_submit():
                edu_plan = request.form.get("edu_plan")
                return redirect(
                    url_for(
                        f"library.{self.lib_type}_upload",
                        plan_id=edu_plan,
                    )
                )
            return render_template(
                self.template_name,
                active="library",
                title=self.title,
                form=form,
                edu_spec=edu_spec,
            )
        return render_template(
            self.template_name,
            active="library",
            title=self.title,
            form=form,
        )


bp.add_url_rule(
    "/library_choose_plan",
    view_func=load_sources_permission_required(
        LibraryChoosePlanView.as_view(
            "library_choose_plan",
            lib_type="library",
            lib_type_name="Литература",
            title="Загрузка списка литературы",
        )
    ),
)
bp.add_url_rule(
    "/library_int_choose_plan",
    view_func=load_internet_links_permission_required(
        LibraryChoosePlanView.as_view(
            "library_int_choose_plan",
            lib_type="library_int",
            lib_type_name="Интернет ресурсы",
            title="Загрузка ресурсов сети Интернет",
        )
    ),
)
bp.add_url_rule(
    "/library_db_choose_plan",
    view_func=load_info_systems_permission_required(
        LibraryChoosePlanView.as_view(
            "library_db_choose_plan",
            lib_type="library_db",
            lib_type_name="Базы и справочные системы",
            title="Загрузка ресурсов баз данных и инф.-справ. систем",
        )
    ),
)
bp.add_url_rule(
    "/library_np_choose_plan",
    view_func=load_science_products_permission_required(
        LibraryChoosePlanView.as_view(
            "library_np_choose_plan",
            lib_type="library_np",
            lib_type_name="Научная продукция",
            title="Загрузка списка научной продукции",
        )
    ),
)


class LibraryUploadView(View):
    methods = ["GET", "POST"]

    def __init__(self, lib_type, lib_type_name, title):
        self.template_name = "library/upload_data.html"
        self.lib_type = lib_type
        self.lib_type_name = lib_type_name
        self.title = title

    @login_required
    async def dispatch_request(self, plan_id):
        form = LibraryForm()
        form.library_plan_content.data = f"{self.lib_type_name} в РП плана"
        plan = EducationPlan(
            education_plan_id=plan_id,
            plan_education_plans=await check_api_db_response(
                await api_get_db_table(
                    ApeksConfig.TABLES.get("plan_education_plans"), id=plan_id
                )
            ),
            plan_curriculum_disciplines=await get_plan_curriculum_disciplines(plan_id),
        )
        if request.method == "POST":
            if request.form.get("library_load_temp"):
                return redirect(
                    url_for(
                        "main.get_temp_file", filename=f"{self.lib_type}_load_temp.xlsx"
                    )
                )
            if request.form.get("library_plan_content"):
                return redirect(
                    url_for(f"library.{self.lib_type}_export", plan_id=plan_id)
                )
            if request.files["file"] and form.validate_on_submit():
                file = request.files["file"]
                if file and allowed_file(file.filename):
                    filename = file.filename
                    file.save(os.path.join(FlaskConfig.UPLOAD_FILE_DIR, filename))
                    if request.form.get("library_check"):
                        # Проверка данных
                        return redirect(
                            url_for(
                                f"library.{self.lib_type}_check",
                                plan_id=plan_id,
                                filename=filename,
                            )
                        )
                    if request.form.get("library_update"):
                        # Загрузка данных
                        return redirect(
                            url_for(
                                f"library.{self.lib_type}_update",
                                plan_id=plan_id,
                                filename=filename,
                            )
                        )
        return render_template(
            self.template_name,
            active="library",
            title=self.title,
            lib_type_name=self.lib_type_name,
            form=form,
            url=ApeksConfig.URL,
            plan_id=plan_id,
            plan_name=plan.name,
        )


bp.add_url_rule(
    "/library_upload/<int:plan_id>",
    view_func=load_sources_permission_required(
        LibraryUploadView.as_view(
            "library_upload",
            lib_type="library",
            lib_type_name="Литература",
            title="Загрузка списка литературы",
        )
    ),
)
bp.add_url_rule(
    "/library_int_upload/<int:plan_id>",
    view_func=load_internet_links_permission_required(
        LibraryUploadView.as_view(
            "library_int_upload",
            lib_type="library_int",
            lib_type_name="Интернет ресурсы",
            title="Загрузка ресурсов сети Интернет",
        )
    ),
)
bp.add_url_rule(
    "/library_db_upload/<int:plan_id>",
    view_func=load_info_systems_permission_required(
        LibraryUploadView.as_view(
            "library_db_upload",
            lib_type="library_db",
            lib_type_name="Базы и справочные системы",
            title="Загрузка ресурсов баз данных и инф.-справ. систем",
        )
    ),
)
bp.add_url_rule(
    "/library_np_upload/<int:plan_id>",
    view_func=load_science_products_permission_required(
        LibraryUploadView.as_view(
            "library_np_upload",
            lib_type="library_np",
            lib_type_name="Научная продукция",
            title="Загрузка списка научной продукции",
        )
    ),
)


class LibraryCheckView(View):
    methods = ["GET", "POST"]

    def __init__(self, lib_type, lib_type_name, title):
        self.template_name = "library/upload_data.html"
        self.lib_type = lib_type
        self.lib_type_name = lib_type_name
        self.title = title

    @login_required
    async def dispatch_request(self, plan_id, filename):
        file = os.path.join(FlaskConfig.UPLOAD_FILE_DIR, filename)
        form = LibraryForm()
        plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
        plan = EducationPlanWorkPrograms(
            education_plan_id=plan_id,
            plan_education_plans=await check_api_db_response(
                await api_get_db_table(
                    ApeksConfig.TABLES.get("plan_education_plans"), id=plan_id
                )
            ),
            plan_curriculum_disciplines=plan_disciplines,
            work_programs_data=await get_work_programs_data(
                curriculum_discipline_id=[*plan_disciplines]
            ),
        )
        lib_data = library_file_processing(file)
        if request.method == "POST":
            if request.files["file"] and form.validate_on_submit():
                file = request.files["file"]
                if file and allowed_file(file.filename):
                    filename = file.filename
                    file.save(os.path.join(FlaskConfig.UPLOAD_FILE_DIR, filename))
                    if request.form.get("library_check"):
                        return redirect(
                            url_for(
                                f"library.{self.lib_type}_check",
                                plan_id=plan_id,
                                filename=filename,
                            )
                        )
            if request.form.get("library_load_temp"):
                return redirect(
                    url_for(
                        "main.get_temp_file", filename=f"{self.lib_type}_load_temp.xlsx"
                    )
                )
            if request.form.get("library_plan_content"):
                return redirect(
                    url_for(f"library.{self.lib_type}_export", plan_id=plan_id)
                )
            if request.form.get("library_update"):
                return redirect(
                    url_for(
                        f"library.{self.lib_type}_update",
                        plan_id=plan_id,
                        filename=filename,
                    )
                )
        # Проверяем что программа находится в загруженном файле
        work_programs, no_data = [], []
        for wp in plan.work_programs_data:
            wp_name = plan.work_programs_data[wp].get("name").strip()
            if wp_name in lib_data:
                work_programs.append(wp_name)
            else:
                no_data.append(wp_name)
        return render_template(
            self.template_name,
            active="library",
            title=self.title,
            lib_type_name=self.lib_type_name,
            form=form,
            url=ApeksConfig.URL,
            plan_id=plan_id,
            plan_name=plan.name,
            no_data=no_data,
            program_non_exist=plan.non_exist,
            program_duplicate=plan.duplicate,
            program_wrong_name=plan.wrong_name,
            work_programs=work_programs,
        )


bp.add_url_rule(
    "/library_check/<int:plan_id>/<string:filename>",
    view_func=load_sources_permission_required(
        LibraryCheckView.as_view(
            "library_check",
            lib_type="library",
            lib_type_name="Литература",
            title="Загрузка списка литературы",
        )
    ),
)
bp.add_url_rule(
    "/library_int_check/<int:plan_id>/<string:filename>",
    view_func=load_internet_links_permission_required(
        LibraryCheckView.as_view(
            "library_int_check",
            lib_type="library_int",
            lib_type_name="Интернет ресурсы",
            title="Загрузка ресурсов сети Интернет",
        )
    ),
)
bp.add_url_rule(
    "/library_db_check/<int:plan_id>/<string:filename>",
    view_func=load_info_systems_permission_required(
        LibraryCheckView.as_view(
            "library_db_check",
            lib_type="library_db",
            lib_type_name="Базы и справочные системы",
            title="Загрузка ресурсов баз данных и инф.-справ. систем",
        )
    ),
)
bp.add_url_rule(
    "/library_np_check/<int:plan_id>/<string:filename>",
    view_func=load_science_products_permission_required(
        LibraryCheckView.as_view(
            "library_np_check",
            lib_type="library_np",
            lib_type_name="Научная продукция",
            title="Загрузка списка научной продукции",
        )
    ),
)


class LibraryUpdateView(View):
    methods = ["GET", "POST"]

    def __init__(self, lib_type, lib_type_name):
        self.lib_type = lib_type
        self.lib_type_name = lib_type_name

    @login_required
    async def dispatch_request(self, plan_id, filename):
        file = os.path.join(FlaskConfig.UPLOAD_FILE_DIR, filename)
        plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
        plan = EducationPlanWorkPrograms(
            education_plan_id=plan_id,
            plan_education_plans=await check_api_db_response(
                await api_get_db_table(
                    ApeksConfig.TABLES.get("plan_education_plans"), id=plan_id
                )
            ),
            plan_curriculum_disciplines=plan_disciplines,
            work_programs_data=await get_work_programs_data(
                curriculum_discipline_id=[*plan_disciplines], fields=True
            ),
        )
        file_data = library_file_processing(file)
        for disc in file_data:
            for wp_id in plan.work_programs_data:
                if plan.work_programs_data[wp_id].get("name").strip() == disc.strip():
                    lib_items = ApeksConfig.LIB_TYPES[self.lib_type]
                    for i in range(len(lib_items)):
                        if lib_items[i] not in plan.work_programs_data[wp_id]["fields"]:
                            await load_lib_add_field(wp_id, lib_items[i])
                        check = 1 if file_data[disc][i] else 0
                        await load_lib_edit_field(
                            wp_id, lib_items[i], file_data[disc][i], check
                        )
        flash(f"Данные из файла - '{filename}': успешно загружены", category="success")
        return redirect(url_for(f"library.{self.lib_type}_upload", plan_id=plan_id))


bp.add_url_rule(
    "/library_update/<int:plan_id>/<string:filename>",
    view_func=load_sources_permission_required(
        LibraryUpdateView.as_view(
            "library_update",
            lib_type="library",
            lib_type_name="Литература",
        )
    ),
)
bp.add_url_rule(
    "/library_int_update/<int:plan_id>/<string:filename>",
    view_func=load_internet_links_permission_required(
        LibraryUpdateView.as_view(
            "library_int_update",
            lib_type="library_int",
            lib_type_name="Интернет ресурсы",
        )
    ),
)
bp.add_url_rule(
    "/library_db_update/<int:plan_id>/<string:filename>",
    view_func=load_info_systems_permission_required(
        LibraryUpdateView.as_view(
            "library_db_update",
            lib_type="library_db",
            lib_type_name="Базы и справочные системы",
        )
    ),
)
bp.add_url_rule(
    "/library_np_update/<int:plan_id>/<string:filename>",
    view_func=load_science_products_permission_required(
        LibraryUpdateView.as_view(
            "library_np_update",
            lib_type="library_np",
            lib_type_name="Научная продукция",
        )
    ),
)


class LibraryExportView(View):
    methods = ["GET", "POST"]

    def __init__(self, lib_type, lib_type_name):
        self.lib_type = lib_type
        self.lib_type_name = lib_type_name

    @login_required
    async def dispatch_request(self, plan_id):
        plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
        plan = EducationPlanWorkPrograms(
            education_plan_id=plan_id,
            plan_education_plans=await check_api_db_response(
                await api_get_db_table(
                    ApeksConfig.TABLES.get("plan_education_plans"), id=plan_id
                )
            ),
            plan_curriculum_disciplines=plan_disciplines,
            work_programs_data=await get_work_programs_data(
                curriculum_discipline_id=[*plan_disciplines], fields=True
            ),
        )
        lib_data = plan.library_content()
        filename = f"{self.lib_type_name} - {plan.name}.xlsx"
        library_report(lib_data, self.lib_type, filename)
        return redirect(url_for("main.get_file", filename=filename))


bp.add_url_rule(
    "/library_export/<int:plan_id>",
    view_func=load_sources_permission_required(
        LibraryExportView.as_view(
            "library_export",
            lib_type="library",
            lib_type_name="Литература",
        )
    ),
)
bp.add_url_rule(
    "/library_int_export/<int:plan_id>",
    view_func=load_internet_links_permission_required(
        LibraryExportView.as_view(
            "library_int_export",
            lib_type="library_int",
            lib_type_name="Интернет ресурсы",
        )
    ),
)
bp.add_url_rule(
    "/library_db_export/<int:plan_id>",
    view_func=load_info_systems_permission_required(
        LibraryExportView.as_view(
            "library_db_export",
            lib_type="library_db",
            lib_type_name="Базы и справочные системы",
        )
    ),
)
bp.add_url_rule(
    "/library_np_export/<int:plan_id>",
    view_func=load_science_products_permission_required(
        LibraryExportView.as_view(
            "library_np_export",
            lib_type="library_np",
            lib_type_name="Научная продукция",
        )
    ),
)
