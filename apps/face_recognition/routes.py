# -*- encoding: utf-8 -*-
"""
Copyright (c) 2022 - VKIST
"""

from flask import request, jsonify, Response, send_file, redirect, render_template
from flask_login import (
    current_user,
    login_required
)
import redis
import torch

import hnswlib
import uuid
import numpy as np
import cv2
import os
import datetime
import calendar

from sqlalchemy import func
from sqlalchemy.sql import text

from facenet_pytorch import MTCNN, InceptionResnetV1

from apps import db
from apps.face_recognition import blueprint
from apps.face_recognition.models import Images, DefineImages, People, FullImages
from apps.authentication.models import SecretKeys

from apps.face_recognition.util import load_image

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, device=device)
resnet = InceptionResnetV1(pretrained='vggface2', device=device).eval()
red = redis.StrictRedis(host='cache', port=6379)

def event_stream(secret_key):
    pubsub = red.pubsub()
    pubsub.subscribe('event_channel_' + secret_key)
    for message in pubsub.listen():
        if message['type']=='message':
            yield 'data: %s\n\n' % message['data'].decode('utf-8')

@blueprint.route('/facerec', methods=['POST'])
def facerec():
    req = request.get_json()

    if 'secret_key' not in req:
        return jsonify({"result": {'message': 'Vui lòng truyền secret key'}}), 400

    secret_key = req['secret_key']
    user = SecretKeys.query.filter_by(secret_key=req['secret_key']).first()
    
    if not user:
        return jsonify({"result": {'message': 'Secret key không hợp lệ'}}), 403

    img_input = ""
    if "img" in list(req.keys()):
        img_input = req["img"]

    validate_img = False
    if len(img_input) > 11 and img_input[0:11] == "data:image/":
        validate_img = True

    if validate_img != True:
        return jsonify({"result": {'message': 'Vui lòng truyền ảnh dưới dạng Base64'}}), 400
    
    img = load_image(img_input)

    full_name = str(uuid.uuid4())

    if not os.path.isdir("/home/data/full_images/" + secret_key):
        os.mkdir("/home/data/full_images/" + secret_key)
    path = "/home/data/full_images/" + secret_key + "/" + full_name + '.jpg'
    cv2.imwrite(path, (img).astype('uint8'))

    imgs = np.expand_dims(img, axis=0)
    imgs, prob = mtcnn(img, save_path=None, return_prob=True)
    if imgs is None:
        return jsonify({"result": {'message': 'Không xác định được khuôn mặt'}}), 400
    imgs = imgs.to(device)
    imgs = [imgs]

    paths = []
    for img in imgs:
        name = str(uuid.uuid4())
        if not os.path.isdir("/home/data/images/" + secret_key):
            os.mkdir("/home/data/images/" + secret_key)
        path = "/home/data/images/" + secret_key + "/" + name + '.jpg'
        cv2.imwrite(path, (img.permute(1,2,0).detach().cpu().numpy()*128 + 127.5).astype('uint8'))
        paths.append(name)

    identities = []
    for result, path in zip(imgs, paths):

        result = resnet(result.unsqueeze(0))

        p = hnswlib.Index(space = 'cosine', dim = 512)
        p.load_index("/home/data/indexes/index_" + str(user.id) + '.bin')
        try:
            neighbors, distances = p.knn_query(result.detach().cpu().numpy(), k=1)
            person_id = -1
            if distances[0][0] < 0.3:
                person_id = db.session.query(DefineImages.person_id, func.count(DefineImages.person_id).label('total'))\
                            .filter(DefineImages.id.in_(neighbors.tolist()[0]))\
                            .filter(DefineImages.user_id==user.id)\
                            .group_by(DefineImages.person_id)\
                            .order_by(text('total DESC')).first().person_id
        except:
            person_id = -1

        person = People.query.filter_by(id=person_id).first()
        identities.append('Người lạ' if not person else person.name)
        image = Images(user_id=user.id, person_id=person_id, image_id=path, embedding=np.array2string(result.detach().cpu().numpy(), separator=','))
        db.session.add(image)
        db.session.commit()

        if person_id != -1:
            image = Images.query.filter_by(image_id=path).first()
            full_image = FullImages(image_id=image.id, full_image_id=full_name, user_id=user.id)
            db.session.add(full_image)
            db.session.commit()

        now = datetime.datetime.now().replace(microsecond=0).time()
        red.publish('event_channel_' + secret_key, u'[%s] %s: %s' % (now.isoformat(), secret_key, 'new image'))

    return jsonify({'result': {"identities": identities, "id": person_id}}), 200


@blueprint.route('/facereg', methods=['POST'])
@login_required
def facereg():
    req = request.get_json()
    if 'image_id' not in req or not ('name' in req or 'access_key' in req):
        return jsonify({"result": {'message': 'Vui lòng truyền id của ảnh và id đối tượng'}}), 400
    
    image_id = req['image_id']
    
    if not ('access_key' in req):
        name = req['name']
        access_key = str(uuid.uuid4())
    else:
        access_key = req['access_key']

    p = hnswlib.Index(space = 'cosine', dim = 512)

    if os.path.isfile("/home/data/indexes/index_" + str(current_user.id) + '.bin'):
        p.load_index("/home/data/indexes/index_" + str(current_user.id) + '.bin', max_elements=1000)

    image_instance = Images.query.filter_by(image_id=image_id).first()
    embedding = image_instance.embedding
    embedding = embedding[2:-2]
    embedding = np.expand_dims(np.fromstring(embedding, dtype='float32', sep=','), axis=0)
    embedding_id = image_instance.id

    if not ('access_key' in req):
        person = People(user_id=current_user.id, name=name, access_key=access_key)
        db.session.add(person)
        db.session.commit()

    person = People.query.filter_by(access_key=access_key).first()
    define_image = DefineImages(user_id=current_user.id, person_id=person.id, embedding_id=embedding_id)
    db.session.add(define_image)
    db.session.commit()

    image_instance = Images.query.filter_by(image_id=image_id).first()
    image_instance.person_id = person.id
    db.session.commit()

    define_image = DefineImages.query.filter_by(embedding_id=embedding_id).first()
    p.add_items(embedding, np.array([define_image.id]))
    p.save_index("/home/data/indexes/index_" + str(current_user.id) + '.bin')

    secret_key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()
    secret_key = secret_key_instance.secret_key
    now = datetime.datetime.now().replace(microsecond=0).time()
    red.publish('event_channel_' + secret_key, u'[%s] %s: %s' % (now.isoformat(), secret_key, 'new person'))

    return jsonify({"result": {'message': 'success'}}), 200


@blueprint.route('/event_stream')
@login_required
def stream():
    key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()
    return Response(event_stream(key_instance.secret_key), mimetype="text/event-stream")

@blueprint.route('/image/<secret_key>/<image_id>')
# @login_required
def image(secret_key, image_id):
    # key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()
    # if key_instance.secret_key != secret_key:
    #     return jsonify({"result": {'message': 'Không có quyền truy cập'}}), 403
    # image_instance = Images.query.filter_by(user_id=str(current_user.id)).filter_by(image_id=image_id).first()
    # if not image_instance:
    #     return jsonify({"result": {'message': 'Ảnh không tồn tại'}}), 404
    return send_file('/home/data/images/' + secret_key + "/" + image_id + '.jpg')

@blueprint.route('/full_image/<secret_key>/<image_id>')
# @login_required
def full_image(secret_key, image_id):
    # key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()
    # if key_instance.secret_key != secret_key:
    #     return jsonify({"result": {'message': 'Không có quyền truy cập'}}), 403
    # image_instance = FullImages.query.filter_by(user_id=str(current_user.id)).filter_by(full_image_id=image_id).first()
    # if not image_instance:
    #     return jsonify({"result": {'message': 'Ảnh không tồn tại'}}), 404
    return send_file('/home/data/full_images/' + secret_key + "/" + image_id + '.jpg')

@blueprint.route('/data', methods=['GET'])
@login_required
def data():
    key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()
    secret_key = key_instance.secret_key

    people_array = db.session.query(DefineImages.person_id, Images.image_id, People.name, People.access_key)\
              .filter(DefineImages.user_id==current_user.id)\
              .filter(People.id==DefineImages.person_id)\
              .filter(Images.id==DefineImages.embedding_id)\
              .group_by(DefineImages.person_id, Images.image_id, People.name, People.access_key)\
              .all()

    current_checkin = db.session.query(Images.person_id, Images.timestamp, Images.image_id, People.name, People.access_key)\
              .filter(Images.user_id==current_user.id)\
              .filter(Images.person_id!=-1)\
              .filter(People.id==Images.person_id)\
              .filter(Images.timestamp >= datetime.datetime.utcnow().strftime('%Y-%m-%d'))\
              .group_by(Images.person_id, Images.image_id, People.name, People.access_key)\
              .all()
    if not current_checkin:
        current_checkin = []
    
    people_array_ = {}
    for u in people_array:
        people_array_[str(u[0])] = {'name': u[2], 'image_id': u[1], 'timestamp': '--', 'access_key':u[3], 'checkin': False}
    for u in current_checkin:
        people_array_[str(u[0])] = {'name': u[3], 'image_id': u[2], 'timestamp': str(u[1]), 'access_key':u[4], 'checkin': True}
    
    number_of_current_checkin = len(current_checkin)
    current_checkin = [people_array_[u] for u in people_array_.keys()]
    number_of_people = len(current_checkin)

    current_timeline = db.session.query(Images.person_id, Images.timestamp, Images.image_id, People.name)\
              .filter(Images.user_id==current_user.id)\
              .filter(People.id==Images.person_id)\
              .order_by(Images.timestamp.desc())\
              .limit(5)\
              .all()
    
    current_timeline = [{'name': u[3] if u[0] != -1 else 'Người lạ', 'image_id': u[2], 'timestamp': str(u[1])} for u in current_timeline]

    strangers = db.session.query(Images.person_id, Images.timestamp, Images.image_id)\
              .filter(Images.user_id==current_user.id)\
              .filter(Images.person_id==-1)\
              .order_by(Images.timestamp.desc())\
              .limit(5)\
              .all()

    strangers = [{'image_id': u[2], 'timestamp': str(u[1])} for u in strangers]

    # day = calendar.monthrange(datetime.datetime.utcnow().year, datetime.datetime.utcnow().month)[1]
    # checkin_data = {}
    # for i in range(1, day+1):
    #     begin_day = datetime.datetime.utcnow().replace(day=i).strftime("%Y-%m-%d")
    #     if i != day:
    #         end_day = datetime.datetime.utcnow().replace(day=i+1).strftime("%Y-%m-%d")
    #     else:
    #         end_day = datetime.datetime.utcnow().replace(day=1).replace(month=datetime.datetime.utcnow().month).strftime("%Y-%m-%d")
    #     checkin = db.session.query(Images.person_id, Images.timestamp, func.count(Images.id))\
    #             .filter(Images.user_id==current_user.id)\
    #             .filter(Images.person_id!=-1)\
    #             .filter(People.id==Images.person_id)\
    #             .filter(Images.timestamp >= begin_day)\
    #             .filter(Images.timestamp < end_day)\
    #             .group_by(Images.person_id, Images.timestamp)\
    #             .all()
    #     checkin_array_ = {}
    #     for u in checkin:
    #         checkin_array_[str(u[0])] = 1
    #     checkin_data[begin_day] = len(checkin_array_.keys())

    return jsonify({
        "result": {
            'secret_key': secret_key,
            'number_of_people': number_of_people,
            'current_checkin': current_checkin,
            'number_of_current_checkin': number_of_current_checkin,
            'current_timeline': current_timeline,
            'strangers': strangers,
            # 'checkin_data': checkin_data
        }
    }), 200

@blueprint.route('/list/<access_key>', methods=['GET'])
@login_required
def statistic(access_key):
    person = People.query.filter_by(access_key=access_key).first()
    if not person:
        return redirect(url_for('home_blueprint.list'))
    person_user = DefineImages.query.filter_by(person_id=person.id).filter_by(user_id=current_user.id).first()
    if not person_user:
        return redirect(url_for('home_blueprint.list'))
    
    people_array = db.session.query(DefineImages.person_id, Images.image_id, People.name, People.access_key)\
              .filter(DefineImages.user_id==current_user.id)\
              .filter(People.id==DefineImages.person_id)\
              .filter(Images.id==DefineImages.embedding_id)\
              .filter(DefineImages.person_id==person.id)\
              .first()

    full_image_array = db.session.query(Images.id, Images.person_id, FullImages.image_id, FullImages.full_image_id)\
              .filter(Images.person_id == person.id)\
              .filter(Images.id==FullImages.image_id)\
              .limit(4)\
              .all()
    full_images = []
    for f in full_image_array:
        full_images.append(f[3])
    
    day = calendar.monthrange(datetime.datetime.utcnow().year, datetime.datetime.utcnow().month)[1]
    begin_day = datetime.datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
    end_day = datetime.datetime.utcnow().replace(day=day).strftime("%Y-%m-%d")
    days = np.busday_count( begin_day, end_day )

    info={'name': people_array[2], 'image_id': people_array[1]}

    secret_key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()

    all_checkin = db.session.query(Images.person_id, Images.timestamp, Images.image_id)\
              .filter(Images.user_id==current_user.id)\
              .filter(Images.person_id==person.id)\
              .filter(Images.timestamp >= begin_day)\
              .filter(Images.timestamp <= end_day)\
              .all()
    checkin_data = {}
    for checkin in all_checkin:
        checkin_data[checkin[1].strftime("%Y-%m-%d")] = {"image_id": checkin[2]}
    checkin_array = []
    i = 0
    for key, value in checkin_data.items():
        checkin_array.append({
            'id': i,
            'title': 'Đã điểm danh',
            'imageurl': '/image/' + secret_key_instance.secret_key + '/' + value['image_id'],
            'start': key,
            'allDay': True,
            'className': 'bg-green',
        })
        i+=1
    info['number_of_checkin'] = len(checkin_array)

    return render_template("home/statistic.html", segment='list', secret_key=secret_key_instance.secret_key, person_info=info, checkin_array=checkin_array, work_days= days, full_images=full_images)

class Object(object):
    pass

@blueprint.route('/parent/<access_key>', methods=['GET'])
def parent_statistic(access_key):
    person = People.query.filter_by(access_key=access_key).first()
    if not person:
        return redirect(url_for('home_blueprint.list'))
    user = DefineImages.query.filter_by(person_id=person.id).first()
    if not user:
        return redirect(url_for('home_blueprint.list'))

    current_user = Object()
    current_user.id = user.user_id
    
    people_array = db.session.query(DefineImages.person_id, Images.image_id, People.name, People.access_key)\
              .filter(DefineImages.user_id==current_user.id)\
              .filter(People.id==DefineImages.person_id)\
              .filter(Images.id==DefineImages.embedding_id)\
              .filter(DefineImages.person_id==person.id)\
              .first()

    full_image_array = db.session.query(Images.id, Images.person_id, FullImages.image_id, FullImages.full_image_id)\
              .filter(Images.person_id == person.id)\
              .filter(Images.id==FullImages.image_id)\
              .limit(4)\
              .all()
    full_images = []
    for f in full_image_array:
        full_images.append(f[3])
    
    day = calendar.monthrange(datetime.datetime.utcnow().year, datetime.datetime.utcnow().month)[1]
    begin_day = datetime.datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
    end_day = datetime.datetime.utcnow().replace(day=day).strftime("%Y-%m-%d")
    days = np.busday_count( begin_day, end_day )

    info={'name': people_array[2], 'image_id': people_array[1]}

    secret_key_instance = SecretKeys.query.filter_by(user_id=current_user.id).first()

    all_checkin = db.session.query(Images.person_id, Images.timestamp, Images.image_id)\
              .filter(Images.user_id==current_user.id)\
              .filter(Images.person_id==person.id)\
              .filter(Images.timestamp >= begin_day)\
              .filter(Images.timestamp <= end_day)\
              .all()
    checkin_data = {}
    for checkin in all_checkin:
        checkin_data[checkin[1].strftime("%Y-%m-%d")] = {"image_id": checkin[2]}
    checkin_array = []
    i = 0
    for key, value in checkin_data.items():
        checkin_array.append({
            'id': i,
            'title': 'Đã điểm danh',
            'imageurl': '/image/' + secret_key_instance.secret_key + '/' + value['image_id'],
            'start': key,
            'allDay': True,
            'className': 'bg-green',
        })
        i+=1
    info['number_of_checkin'] = len(checkin_array)

    return render_template("home/parent.html", segment='list', secret_key=secret_key_instance.secret_key, person_info=info, checkin_array=checkin_array, work_days= days, full_images=full_images)

@blueprint.route('/change_name', methods=['POST'])
@login_required
def change_name():
    req = request.get_json()
    if 'access_key' not in req or 'name' not in req:
        return jsonify({"result": {'message': 'Vui lòng truyền access_key và tên'}}), 400
    
    access_key = req['access_key']
    name = req['name']

    person = People.query.filter_by(access_key=access_key).first()
    if not person:
        return jsonify({"result": {'message': 'Đối tượng không tồn tại'}}), 404

    user = DefineImages.query.filter_by(person_id=person.id).first()
    if not person:
        return jsonify({"result": {'message': 'Quyền truy cập bị từ trối'}}), 403

    person = People.query.filter_by(access_key=access_key).first()
    person.name = name
    db.session.commit()

    return jsonify({"result": {'message': 'Thành công'}}), 200
