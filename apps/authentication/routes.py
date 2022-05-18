# -*- encoding: utf-8 -*-
"""
Copyright (c) 2022 - VKIST
"""

from flask import render_template, redirect, request, url_for, jsonify
from flask_login import (
    current_user,
    login_user,
    logout_user,
    login_required
)

import uuid
import hnswlib

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm, CreateUserInfoForm
from apps.authentication.models import Users, SecretKeys, UsersInfo

from apps.authentication.util import verify_pass


@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))


# Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        user = Users.query.filter_by(username=username).first()

        # Check the password
        if user and verify_pass(password, user.password):

            login_user(user)
            return redirect(url_for('authentication_blueprint.route_default'))

        # Something (user or pass) is not ok
        return render_template('accounts/login.html',
                               msg='Wrong user or password',
                               form=login_form)

    if not current_user.is_authenticated:
        return render_template('accounts/login.html',
                               form=login_form)
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        user = Users.query.filter_by(email=email).first()
        secret_key = str(uuid.uuid4())
        secret_key_instance = SecretKeys(user_id=user.id, secret_key=secret_key)
        db.session.add(secret_key_instance)
        db.session.commit()

        p = hnswlib.Index(space = 'cosine', dim = 512)
        p.init_index(max_elements = 1000, ef_construction = 200, M = 16)
        p.set_ef(10)
        p.set_num_threads(4)
        p.save_index("/home/data/indexes/index_" + str(user.id) + ".bin")

        return render_template('accounts/register.html',
                               msg='User created please <a href="/login">login</a>',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('accounts/register.html', form=create_account_form)


@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))

@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    create_userinfo_form = CreateUserInfoForm(request.form)
    
    if request.method == 'POST':
        info = UsersInfo.query.filter_by(phone=request.form['phone']).first()
        if not info:
            user_info = UsersInfo(address=request.form['address'], phone=request.form['phone'], user_id=current_user.id)
            db.session.add(user_info)
        else:
            info.address = request.form['address']
        db.session.commit()

    user = SecretKeys.query.filter_by(user_id=current_user.id).first()
    user_info = UsersInfo.query.filter_by(user_id=current_user.id).first()
    address = ""
    phone = ""
    if user_info:
        address = user_info.address
        phone = user_info.phone
    return render_template("home/profile.html", segment='profile', info={"secret_key": user.secret_key, "address": address, "phone": phone}, form=create_userinfo_form)

# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
