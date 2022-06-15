from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash
from flask.views import View
from flask_login import login_required

from app.common.classes.EducationPlan import (
    EducationPlanExtended,
    EducationPlanWorkProgram,
)
from app.common.classes.EducationStaff import EducationStaff
from app.common.exceptions import ApeksWrongParameterException, \
    ApeksParameterNonExistException
from app.common.func.api_get import (
    get_departments,
    check_api_db_response,
    api_get_db_table,
    get_plan_curriculum_disciplines,
    get_organization_name,
    get_organization_chief_info,
    get_rank_name,
    get_plan_education_specialties,
    get_education_plans,
    get_work_programs_data,
    get_state_staff,
)
from app.common.func.api_post import (
    work_programs_dates_update,
    edit_work_programs_data,
    create_work_program, work_program_add_parameter,
)
from app.common.func.app_core import (
    data_processor,
    work_program_field_tb_table,
    work_program_get_parameter_info,
)
from app.common.reports.wp_title_pages import generate_wp_title_pages
from app.main.func import db_filter_req
from app.programs import bp
from app.programs.forms import (
    WorkProgramDatesUpdate,
    FieldsForm,
    ChoosePlan,
    DepartmentWPCheck,
    WorkProgramFieldUpdate,
    TitlePagesGenerator,
)
from app.programs.models import WorkProgramBunchData
from config import ApeksConfig as Apeks


class ProgramsChoosePlanView(View):
    methods = ["GET", "POST"]

    def __init__(self, wp_type, title):
        self.template_name = "programs/programs_choose_plan.html"
        self.wp_type = wp_type
        self.title = title

    @login_required
    async def dispatch_request(self):
        form = ChoosePlan()
        specialities = await get_plan_education_specialties()
        form.edu_spec.choices = list(specialities.items())
        if request.method == "POST":
            edu_spec = request.form.get("edu_spec")
            plans = await get_education_plans(edu_spec)
            form.edu_plan.choices = list(plans.items())
            if request.form.get("edu_plan") and form.validate_on_submit():
                edu_plan = request.form.get("edu_plan")
                return redirect(
                    url_for(
                        f"programs.{self.wp_type}",
                        plan_id=edu_plan,
                    )
                )
            return render_template(
                self.template_name,
                active="programs",
                title=self.title,
                form=form,
                edu_spec=edu_spec,
            )
        return render_template(
            self.template_name,
            active="programs",
            title=self.title,
            form=form,
        )


bp.add_url_rule(
    "/wp_fields_choose_plan",
    view_func=ProgramsChoosePlanView.as_view(
        "wp_fields_choose_plan",
        wp_type="wp_fields",
        title="Сводная информация по полям рабочих программ плана",
    ),
)

bp.add_url_rule(
    "/wp_data_choose_plan",
    view_func=ProgramsChoosePlanView.as_view(
        "wp_data_choose_plan",
        wp_type="wp_data",
        title="Информация по рабочим программам учебного плана",
    ),
)

bp.add_url_rule(
    "/wp_title_choose_plan",
    view_func=ProgramsChoosePlanView.as_view(
        "wp_title_choose_plan",
        wp_type="wp_title",
        title="Формирование титульных листов рабочих программ",
    ),
)


@bp.route("/wp_dept_check", methods=["GET", "POST"])
async def wp_dept_check():
    form = DepartmentWPCheck()
    departments = await get_departments()
    form.department.choices = [(k, v.get("full")) for k, v in departments.items()]
    specialities = await get_plan_education_specialties()
    form.edu_spec.choices = list(specialities.items())
    if request.method == "POST":
        programs_info = {}
        edu_spec = request.form.get("edu_spec")
        department = request.form.get("department")
        year = request.form.get("year")
        parameter = request.form.get("wp_fields")
        field_db_table = work_program_field_tb_table(parameter)
        db_sections = (
            True if field_db_table == Apeks.TABLES.get("mm_sections") else False
        )
        db_fields = (
            True
            if field_db_table == Apeks.TABLES.get("mm_work_programs_data")
            else False
        )
        plan_list = await get_education_plans(edu_spec, year=year)
        if plan_list:
            for plan_id in plan_list:
                plan_disciplines = await get_plan_curriculum_disciplines(
                    plan_id, department_id=department
                )
                plan = EducationPlanWorkProgram(
                    education_plan_id=plan_id,
                    plan_education_plans=await check_api_db_response(
                        await api_get_db_table(
                            Apeks.TABLES.get("plan_education_plans"), id=plan_id
                        )
                    ),
                    plan_curriculum_disciplines=plan_disciplines,
                    work_programs_data=await get_work_programs_data(
                        curriculum_discipline_id=[*plan_disciplines],
                        sections=db_sections,
                        fields=db_fields,
                    ),
                )
                programs_info[plan.name] = {}
                for disc in plan.disc_wp_match:
                    disc_name = plan.discipline_name(disc)
                    programs_info[plan.name][disc_name] = {}
                    if not plan.disc_wp_match[disc]:
                        programs_info[plan.name][disc_name][
                            "none"
                        ] = "-->Программа отсутствует<--"
                    else:
                        for wp in plan.disc_wp_match[disc]:
                            try:
                                field_data = work_program_get_parameter_info(
                                    plan.work_programs_data[wp], parameter
                                )
                            except ApeksParameterNonExistException:
                                await work_program_add_parameter(
                                    wp, parameter
                                )
                                field_data = ""
                            else:
                                field_data = "" if not field_data else field_data
                            programs_info[plan.name][disc_name][wp] = field_data
        else:
            programs_info = {
                "Нет планов": {
                    "Нет дисциплин": {"Нет программы": "Информация отсутствует"}
                }
            }
        return render_template(
            "programs/wp_dept_check.html",
            active="programs",
            form=form,
            edu_spec=edu_spec,
            department=department,
            year=year,
            wp_field=parameter,
            wp_data=programs_info,
        )
    return render_template("programs/wp_dept_check.html", active="programs", form=form)


@bp.route("/wp_dates_update", methods=["GET", "POST"])
@login_required
async def wp_dates_update():
    form = WorkProgramDatesUpdate()
    specialities = await get_plan_education_specialties()
    form.edu_spec.choices = list(specialities.items())
    if request.method == "POST":
        edu_spec = request.form.get("edu_spec")
        plans = await get_education_plans(edu_spec)
        form.edu_plan.choices = list(plans.items())
        if request.form.get("wp_dates_update") and form.validate_on_submit():
            plan_id = request.form.get("edu_plan")
            plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
            plan = EducationPlanWorkProgram(
                education_plan_id=plan_id,
                plan_education_plans=await check_api_db_response(
                    await api_get_db_table(
                        Apeks.TABLES.get("plan_education_plans"), id=plan_id
                    )
                ),
                plan_curriculum_disciplines=plan_disciplines,
                work_programs_data=await get_work_programs_data(
                    curriculum_discipline_id=[*plan_disciplines]
                ),
            )
            wp_list = [*plan.work_programs_data]
            response = await work_programs_dates_update(
                wp_list,
                date_methodical=request.form.get("date_methodical") or "",
                document_methodical=request.form.get("document_methodical") or "",
                date_academic=request.form.get("date_academic") or "",
                document_academic=request.form.get("document_academic") or "",
                date_approval=request.form.get("date_approval") or "",
            )
            results = [
                f"Обновлено {response.get('data')} из {len(plan.work_programs_data)}:"
            ]
            results.extend(
                [
                    plan.work_programs_data[wp].get("name")
                    for wp in plan.work_programs_data
                ]
            )
            non_exist = [plan.discipline_name(disc) for disc in plan.non_exist]
            return render_template(
                "programs/wp_dates_update.html",
                active="programs",
                form=form,
                edu_plan=plan_id,
                edu_spec=edu_spec,
                results=results,
                non_exist=non_exist,
            )
        else:
            return render_template(
                "programs/wp_dates_update.html",
                active="programs",
                form=form,
                edu_spec=edu_spec,
            )
    return render_template("programs/wp_dates_update.html", active="programs", form=form)


@bp.route("/wp_fields/<int:plan_id>", methods=["GET", "POST"])
@login_required
async def wp_fields(plan_id):
    form = FieldsForm()
    plan_education_plans = await check_api_db_response(
        await api_get_db_table(
            Apeks.TABLES.get("plan_education_plans"), id=plan_id
        )
    )
    plan_name = plan_education_plans[0].get('name')
    if request.method == "POST":
        parameter = request.form.get("wp_fields")
        field_db_table = work_program_field_tb_table(parameter)
        db_sections = (
            True if field_db_table == Apeks.TABLES.get("mm_sections") else False
        )
        db_fields = (
            True
            if field_db_table == Apeks.TABLES.get("mm_work_programs_data")
            else False
        )
        plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
        plan = EducationPlanWorkProgram(
            education_plan_id=plan_id,
            plan_education_plans=await check_api_db_response(
                await api_get_db_table(
                    Apeks.TABLES.get("plan_education_plans"), id=plan_id
                )
            ),
            plan_curriculum_disciplines=plan_disciplines,
            work_programs_data=await get_work_programs_data(
                curriculum_discipline_id=[*plan_disciplines],
                sections=db_sections,
                fields=db_fields,
            ),
        )
        programs_info = {}
        programs_info[plan.name] = {}
        for disc in plan.disc_wp_match:
            disc_name = plan.discipline_name(disc)
            programs_info[plan.name][disc_name] = {}
            if not plan.disc_wp_match[disc]:
                programs_info[plan.name][disc_name][
                    "none"
                ] = "-->Программа отсутствует<--"
            else:
                for wp in plan.disc_wp_match[disc]:
                    try:
                        field_data = work_program_get_parameter_info(
                            plan.work_programs_data[wp], parameter
                        )
                    except ApeksParameterNonExistException:
                        await work_program_add_parameter(
                            wp, parameter
                        )
                        field_data = ""
                    else:
                        field_data = "" if not field_data else field_data
                    programs_info[plan.name][disc_name][wp] = field_data
        else:
            programs_info = {
                "Нет планов": {
                    "Нет дисциплин": {"Нет программы": "Информация отсутствует"}
                }
            }

        return render_template(
            "programs/wp_fields.html",
            active="programs",
            form=form,
            plan_name=plan_name,
            wp_field=parameter,
            wp_data=programs_info,
        )
    return render_template(
        "programs/wp_fields.html", active="programs", form=form, plan_name=plan_name
    )


@bp.route("/wp_field_edit", methods=["GET", "POST"])
@login_required
async def wp_field_edit():
    form = WorkProgramFieldUpdate()
    wp_id = int(request.args.get("wp_id"))
    parameter = request.args.get("parameter")
    if request.method == "POST":
        parameter = request.form.get("wp_fields")
        if request.form.get("fields_data"):
            return redirect(url_for("programs.wp_field_edit", wp_id=wp_id, parameter=parameter))
        if request.form.get("field_update") and form.validate_on_submit():
            load_data = request.form.get("wp_field_edit")
            kwargs = {parameter: load_data}
            try:
                await edit_work_programs_data(wp_id, **kwargs)
                flash("Данные обновлены")
            except ApeksWrongParameterException:
                if parameter == "department_data":
                    parameter1 = Apeks.MM_WORK_PROGRAMS.get('date_department')
                    d = load_data.split("\r\n")[0].replace("Дата заседания кафедры:", "").replace(" ", "")
                    d = datetime.strptime(d, '%d.%m.%Y')
                    p1_data = date.isoformat(d)
                    parameter2 = Apeks.MM_WORK_PROGRAMS.get('document_department')
                    p2_data = load_data.split("\r\n")[1].replace("Протокол №", "").replace(" ", "")
                    kwargs = {parameter1: p1_data, parameter2: p2_data}
                    await edit_work_programs_data(wp_id, **kwargs)
                    flash("Данные обновлены")
                else:
                    flash(f"Передан неверный параметр: {parameter}")

    form.wp_fields.data = parameter
    db_sections = True if parameter in Apeks.MM_SECTIONS else False
    db_fields = True if parameter in Apeks.MM_WORK_PROGRAMS_DATA else False
    work_program_data = await get_work_programs_data(
        id=wp_id, fields=db_fields, sections=db_sections
    )
    try:
        form.wp_field_edit.data = work_program_get_parameter_info(
            work_program_data[wp_id], parameter
        )
    except ApeksWrongParameterException:
        form.wp_field_edit.data = f"ApeksWrongParameterException {work_program_data[wp_id]}"
        flash(f"Передан неверный параметр: {parameter}")
    except ApeksParameterNonExistException:
        await work_program_add_parameter(
            wp_id, parameter
        )
        form.wp_field_edit.data = ""

    return render_template(
        "programs/wp_field_edit.html",
        active="programs",
        form=form,
        wp_name=work_program_data[wp_id].get("name"),
    )


@bp.route("/wp_data/<int:plan_id>", methods=["GET", "POST"])
@login_required
async def wp_data(plan_id):
    plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
    plan = EducationPlanWorkProgram(
        education_plan_id=plan_id,
        plan_education_plans=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_plans"), id=plan_id)
        ),
        plan_curriculum_disciplines=plan_disciplines,
        work_programs_data=await get_work_programs_data(
            curriculum_discipline_id=[*plan_disciplines], signs=True
        ),
    )
    if request.method == "POST":
        if request.form.get("wp_status_0"):
            await edit_work_programs_data(
                [*plan.work_programs_data],
                status=0,
            )
        elif request.form.get("wp_status_1"):
            await edit_work_programs_data(
                [*plan.work_programs_data],
                status=1,
            )
        elif request.form.get("create_wp"):
            staff = EducationStaff(
                year=datetime.today().year,
                month_start=datetime.today().month,
                month_end=datetime.today().month,
                state_staff=await get_state_staff(),
                state_staff_history=await check_api_db_response(
                    await api_get_db_table(
                        Apeks.TABLES.get("state_staff_history"),
                    )
                ),
                state_staff_positions=await check_api_db_response(
                    await api_get_db_table(Apeks.TABLES.get("state_staff_positions"))
                ),
                departments=await get_departments(),
            )
            for disc_id in plan.non_exist:
                dept_id = plan.plan_curriculum_disciplines[disc_id].get("department_id")
                staff_id = [*staff.department_staff(dept_id)]
                user_id = staff.state_staff[staff_id[0]].get("user_id")
                disc_name = plan.plan_curriculum_disciplines[disc_id].get("name")
                await create_work_program(disc_id, disc_name, user_id)
        return redirect(url_for("programs.wp_data", plan_id=plan_id))

    sign_users = []
    for wp in plan.work_programs_data:
        signs_data = plan.work_programs_data[wp].get("signs")
        if signs_data:
            for user_id, timestamp in signs_data.items():
                sign_users.append(user_id)
    sign_users_data = data_processor(
        await check_api_db_response(
            await api_get_db_table(
                Apeks.TABLES.get("system_users"),
                id=sign_users,
            )
        )
    )

    programs = {}
    for wp in plan.work_programs_data:
        programs[wp] = {}
        signs = []
        signs_data = plan.work_programs_data[wp].get("signs")
        if signs_data:
            for user_id, timestamp in signs_data.items():
                signs.append(
                    f"{sign_users_data[user_id].get('name')}\r\n" f"({timestamp})"
                )
                sign_users.append(user_id)
        else:
            signs.append("Не согласована")

        programs[wp]["disc_id"] = plan.work_programs_data[wp].get(
            "curriculum_discipline_id"
        )
        programs[wp]["name"] = f'"{plan.work_programs_data[wp].get("name")}"'
        programs[wp]["signs"] = signs
        programs[wp]["status"] = plan.work_programs_data[wp].get("status")

    return render_template(
        "programs/wp_data.html",
        active="programs",
        url=Apeks.URL,
        plan_name=plan.name,
        programs=programs,
        no_program=plan.non_exist,
        duplicate=plan.duplicate,
        wrong_name=plan.wrong_name,
        sign_users_data=sign_users_data,
    )


@bp.route("/wp_title/<int:plan_id>", methods=["GET", "POST"])
@login_required
async def wp_title(plan_id):
    plan_disciplines = await get_plan_curriculum_disciplines(plan_id)
    plan = EducationPlanExtended(
        education_plan_id=plan_id,
        plan_education_plans=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_plans"), id=plan_id)
        ),
        plan_curriculum_disciplines=plan_disciplines,
        work_programs_data=await get_work_programs_data(
            curriculum_discipline_id=[*plan_disciplines]
        ),
        plan_education_levels=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_levels"))
        ),
        plan_education_specialties=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_specialties"))
        ),
        plan_education_groups=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_groups"))
        ),
        plan_education_specializations=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_specializations"))
        ),
        plan_education_plans_education_forms=await check_api_db_response(
            await api_get_db_table(
                Apeks.TABLES.get("plan_education_plans_education_forms")
            )
        ),
        plan_education_forms=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_education_forms"))
        ),
        plan_qualifications=await check_api_db_response(
            await api_get_db_table(Apeks.TABLES.get("plan_qualifications"))
        ),
        plan_education_specializations_narrow=await check_api_db_response(
            await api_get_db_table(
                Apeks.TABLES.get("plan_education_specializations_narrow")
            )
        ),
    )
    plan_name = plan.name
    form = TitlePagesGenerator()
    organization_name = await get_organization_name()
    chief_info = await get_organization_chief_info()
    chief_rank = await get_rank_name(chief_info.get("specialRank"))
    approval_date = date.today()
    full_spec_code = (
        f"{plan.education_group_code}."
        f"{plan.education_level_code}."
        f"{plan.specialty_code}"
    )
    form.organization_name.data = organization_name.upper()
    form.chief_rank.data = chief_rank[0]
    form.chief_name.data = chief_info.get("name_short")
    form.wp_approval_day.data = approval_date.day
    form.wp_approval_month.data = approval_date.month
    form.wp_approval_year.data = approval_date.year
    form.wp_speciality_type.data = "bak" if plan.specialty_code == "02" else "spec"
    form.wp_speciality.data = f"{full_spec_code} {plan.specialty}"
    form.wp_specialization_type.data = "bak" if plan.specialty_code == "02" else "spec"
    form.wp_specialization.data = plan.specialization
    form.wp_education_form.data = plan.education_form
    form.wp_year.data = date.today().year
    form.wp_qualification.data = plan.qualification
    form.wp_narrow_specialization.data = plan.specialization_narrow
    if request.method == "POST" and form.validate_on_submit():
        form_data = request.form.to_dict()
        del form_data["csrf_token"]
        del form_data["fields_data"]
        form_data["wp_speciality_type"] = dict(form.wp_speciality_type.choices).get(
            form.wp_speciality_type.data
        )
        form_data["wp_specialization_type"] = dict(
            form.wp_specialization_type.choices
        ).get(form.wp_specialization_type.data)
        form_data["wp_approval_month"] = dict(form.wp_approval_month.choices).get(
            form.wp_approval_month.data
        )
        filename = generate_wp_title_pages(
            form_data, plan_name, plan.work_programs_data
        )
        return redirect(url_for("main.get_file", filename=filename))
    return render_template(
        "programs/wp_title.html",
        active="programs",
        plan_name=plan_name,
        form=form,
    )
