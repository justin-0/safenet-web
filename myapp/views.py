from django.contrib import messages
from django.contrib.auth import authenticate,login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from . models import *
from .face_training import train_face_recognition
from datetime import datetime,date
# Create your views here.


def home(request):
    return render(request,'public_home.html')




@csrf_exempt
def login(request):
    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            auth_login(request, user)
            request.session['user_id'] = user.id

            if user.groups.filter(name='admin').exists():
                return redirect('admin_home')

            elif user.groups.filter(name='authority').exists():
                authority = Authority.objects.filter(USER=user).first()
                if authority:
                    request.session['authority_id'] = authority.id
                    return redirect('authority_home')

                messages.error(request, 'Authority account not found')
                return redirect('login')

            else:
                messages.error(request, 'Access denied')
                return redirect('login')

        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')

    return render(request, 'login.html')




@login_required(login_url='login')
@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login')

# ================================== ADMIN ======================================================================


@login_required(login_url='login')
@never_cache
def admin_home(request):
    return  render(request,'admin_home.html')


@csrf_exempt
def admin_add_authority(request):
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        name = request.POST["name"]
        email = request.POST["email"]
        phone = request.POST["phone"]
        place = request.POST["place"]

        photo1 = request.FILES.get("photo1")
        photo2 = request.FILES.get("photo2")
        photo3 = request.FILES.get("photo3")

        license_proof = request.FILES["license_proof"]

        if User.objects.filter(username=username).exists():
            messages.error(request,'username already exists!')
            return redirect('authority_register')

        user = User.objects.create_user(
            username=username,
            password=password
        )

        group = Group.objects.get(name='authority')
        user.groups.add(group)

        authority = Authority.objects.create(
            USER=user,
            photo1=photo1,
            name=name,
            email=email,
            phone=phone,
            place=place,
            license_proof=license_proof
        )

        import os
        from django.conf import settings

        training_base = os.path.join(settings.MEDIA_ROOT, "authority_training")
        authority_folder = os.path.join(training_base, f"authority_{authority.id}")
        os.makedirs(authority_folder, exist_ok=True)

        photo_paths = []

        if photo1:
            path1 = os.path.join(authority_folder, "photo1.jpg")
            with open(path1, 'wb+') as f:
                for chunk in photo1.chunks():
                    f.write(chunk)
            photo_paths.append(path1)

        if photo2:
            path2 = os.path.join(authority_folder, "photo2.jpg")
            with open(path2, 'wb+') as f:
                for chunk in photo2.chunks():
                    f.write(chunk)
            photo_paths.append(path2)

        if photo3:
            path3 = os.path.join(authority_folder, "photo3.jpg")
            with open(path3, 'wb+') as f:
                for chunk in photo3.chunks():
                    f.write(chunk)
            photo_paths.append(path3)

        print("TRAINING STARTED FOR AUTHORITY:", authority.id)
        print("PHOTO PATHS:", photo_paths)

        train_face_recognition(
            person_id=authority.id,
            category='authority',
            photo_paths=photo_paths
        )

        messages.success(request,'Registration successful')
        return redirect('admin_view_authority')

    return render(request,'admin_add_authority.html')


@login_required(login_url='login')
@never_cache
def admin_view_authority(request):
    authorities = Authority.objects.all()
    return render(request, 'admin_view_authority.html', {'authorities': authorities})


@login_required(login_url='login')
@never_cache
def admin_delete_authority(request, id):

    authority = Authority.objects.get(id=id)
    user = authority.USER

    import os
    import shutil
    from django.conf import settings
    from .face_training import delete_person_from_model

    # delete training images folder
    training_base = os.path.join(settings.MEDIA_ROOT, "authority_training")
    authority_folder = os.path.join(training_base, f"authority_{authority.id}")

    if os.path.exists(authority_folder):
        shutil.rmtree(authority_folder)

    # remove from AI face recognition model
    delete_person_from_model(
        person_id=authority.id,
        category='authority'
    )

    # delete database records
    authority.delete()
    user.delete()

    messages.success(request, 'Authority deleted successfully')

    return redirect('admin_view_authority')

# ========================

from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.conf import settings
import cv2
import os
import time
from datetime import datetime

from .face_detection import process_frame
from .models import UnauthorizedEntry, Camera


camera = None
camera_running = False


def admin_detect_unauthorized_entries(request):

    global camera, camera_running

    if request.GET.get("action") == "start":

        camera = cv2.VideoCapture(0)
        camera_running = True

        capture_start = None
        captured_images = 0
        session_folder = None
        folder = None

        CAPTURE_DURATION = 6
        MAX_IMAGES = 10

        def generate_frames():

            nonlocal capture_start, captured_images, session_folder, folder
            global camera_running

            while camera_running:

                success, frame = camera.read()
                if not success:
                    break

                processed_frame, detections = process_frame(frame)

                for det in detections:

                    if not det['recognized']:

                        if capture_start is None:

                            capture_start = time.time()
                            captured_images = 0

                            session_folder = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                            folder = os.path.join(
                                settings.MEDIA_ROOT,
                                "unauthorized_faces",
                                session_folder
                            )

                            os.makedirs(folder, exist_ok=True)

                        if time.time() - capture_start <= CAPTURE_DURATION:

                            if captured_images < MAX_IMAGES:

                                x1, y1, x2, y2 = det['box']
                                face = frame[y1:y2, x1:x2]

                                filename = f"{captured_images}.jpg"
                                save_path = os.path.join(folder, filename)

                                cv2.imwrite(save_path, face)

                                if captured_images == 0:
                                    UnauthorizedEntry.objects.create(
                                        camera=Camera.objects.first(),
                                        image=f"unauthorized_faces/{session_folder}/{filename}",
                                        detected_time=str(datetime.now())
                                    )

                                captured_images += 1

                        else:
                            capture_start = None

                ret, buffer = cv2.imencode('.jpg', processed_frame)
                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            if camera:
                camera.release()

        return StreamingHttpResponse(
            generate_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )

    if request.GET.get("action") == "stop":

        camera_running = False

        if camera:
            camera.release()

    entries = UnauthorizedEntry.objects.all().order_by('-id')

    data = []

    for entry in entries:

        folder_path = os.path.dirname(entry.image.path)

        images = []

        if os.path.exists(folder_path):

            for file in sorted(os.listdir(folder_path)):

                images.append(
                    f"/media/unauthorized_faces/{os.path.basename(folder_path)}/{file}"
                )

        data.append({
            "entry": entry,
            "images": images
        })

    return render(
        request,
        "admin_detect_unauthorized_entries.html",
        {"entries": data}
    )





# =====================================

@login_required(login_url='login')
@never_cache
def admin_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')

        Category.objects.create(
            category_name=category_name
        )

        messages.success(request, 'Category added successfully')
        return redirect('admin_category')

    categories = Category.objects.all()
    return render(request, 'admin_category.html', {'categories': categories})


@login_required(login_url='login')
@never_cache
def admin_delete_category(request, id):
    category = Category.objects.get(id=id)
    category.delete()

    messages.success(request, 'Category deleted successfully')
    return redirect('admin_category')



@login_required(login_url='login')
@never_cache
def admin_edit_category(request, id):
    category = Category.objects.get(id=id)

    if request.method == 'POST':
        category.category_name = request.POST.get('category_name')
        category.save()

        messages.success(request, 'Category updated successfully')
        return redirect('admin_category')

    return render(request, 'admin_edit_category.html', {'category': category})

# === authority =====================================================================================================




@login_required(login_url='login')
@never_cache
def authority_home(request):
    return render(request,'authority_home.html')


@login_required(login_url='login')
@never_cache
def authority_profile(request):
    authority = Authority.objects.get(USER=request.user)
    return render(request,'authority_profile.html',{'authority':authority})


@login_required(login_url='login')
@never_cache
def authority_edit_profile(request):

    authority = Authority.objects.get(USER=request.user)

    if request.method == 'POST':

        authority.name = request.POST.get('name')
        authority.email = request.POST.get('email')
        authority.phone = request.POST.get('phone')
        authority.place = request.POST.get('place')

        # allow license update only
        if 'license_proof' in request.FILES:
            authority.license_proof = request.FILES['license_proof']

        authority.save()

        messages.success(request, 'Profile updated successfully')

        return redirect('authority_profile')

    return render(
        request,
        'authority_edit_profile.html',
        {'authority': authority}
    )



@login_required(login_url='login')
@never_cache
def authority_view_worker(request):

    workers = Worker.objects.all()

    return render(
        request,
        'authority_view_worker.html',
        {'workers': workers}
    )



@login_required(login_url='login')
@never_cache
def authority_approve_worker(request, wid):

    worker = Worker.objects.get(id=wid)
    worker.status = 'approved'
    worker.save()

    return redirect('authority_view_worker')


@login_required(login_url='login')
@never_cache
def authority_reject_worker(request, wid):

    worker = Worker.objects.get(id=wid)
    worker.status = 'rejected'
    worker.save()

    return redirect('authority_view_worker')




@login_required(login_url='login')
@never_cache
def authority_view_resident(request):

    residents = Resident.objects.all()

    return render(
        request,
        'authority_view_resident.html',
        {'residents': residents}
    )


@login_required(login_url='login')
@never_cache
def authority_approve_resident(request, rid):

    resident = Resident.objects.get(id=rid)
    resident.status = 'approved'
    resident.save()

    return redirect('authority_view_resident')


@login_required(login_url='login')
@never_cache
def authority_reject_resident(request, rid):

    resident = Resident.objects.get(id=rid)
    resident.status = 'rejected'
    resident.save()

    return redirect('authority_view_resident')



@login_required(login_url='login')
@never_cache
def authority_view_resident_complaints(request):

    aid = request.session['authority_id']

    authority = Authority.objects.get(id=aid)

    complaints = Complaint.objects.filter(receiver=authority)

    return render(request,'authority_view_resident_complaints.html',{
        'complaints':complaints
    })


@login_required(login_url='login')
@never_cache
def authority_send_reply(request, cid):
    complaint = Complaint.objects.get(id=cid)

    if request.method == 'POST':
        reply = request.POST['reply']

        complaint.reply = reply
        complaint.status = 'replied'
        complaint.save()

        return redirect('authority_view_resident_complaints')

    return render(request, 'authority/send_reply.html', {
        'complaint': complaint
    })


@login_required(login_url='login')
@never_cache
def admin_view_residents(request):

    residents = Resident.objects.all()

    return render(request,'admin_view_residents.html',{
        'residents':residents
    })


@login_required(login_url='login')
@never_cache
def admin_view_resident_complaints(request,rid):

    complaints = Complaint.objects.filter(sender=rid)

    return render(request,'admin_view_resident_complaints.html',{
        'complaints':complaints
    })


@login_required(login_url='login')
@never_cache
def admin_view_workers(request):

    workers = Worker.objects.all()

    return render(request,'admin_view_workers.html',{
        'workers':workers
    })



@login_required(login_url='login')
@never_cache
def admin_view_worker_request_history(request,wid):

    requests = WorkerRequest.objects.filter(WORKER=wid)

    return render(request,'admin_view_worker_request_history.html',{
        'requests':requests
    })



@login_required(login_url='login')
@never_cache
def admin_add_camera(request):

    if request.method == 'POST':
        camera_name = request.POST['camera_name']
        latitude = request.POST['latitude']
        longitude = request.POST['longitude']

        Camera.objects.create(
            camera_name=camera_name,
            latitude=latitude,
            longitude=longitude
        )

        return redirect('admin_add_camera')

    cameras = Camera.objects.all()

    return render(request,'admin_add_camera.html',{
        'cameras':cameras
    })


@login_required(login_url='login')
@never_cache
def admin_edit_camera(request,cid):

    camera = Camera.objects.get(id=cid)

    if request.method == 'POST':
        camera.camera_name = request.POST['camera_name']
        camera.latitude = request.POST['latitude']
        camera.longitude = request.POST['longitude']
        camera.save()

        return redirect('admin_add_camera')

    return render(request,'admin_edit_camera.html',{
        'camera':camera
    })


@login_required(login_url='login')
@never_cache
def admin_delete_camera(request,cid):

    camera = Camera.objects.get(id=cid)
    camera.delete()

    return redirect('admin_add_camera')

@login_required(login_url='login')
@never_cache
def admin_view_stray_dog_alerts(request):

    alerts = StrayDogAlert.objects.all().order_by('-id')

    return render(request,'admin_view_stray_dog_alerts.html',{
        'alerts':alerts
    })


@login_required(login_url='login')
@never_cache
def admin_view_unauthorized_entries(request):

    data = UnauthorizedEntry.objects.all().order_by('-id')

    return render(request,'admin_view_unauthorized_entries.html',{'data':data})


@login_required(login_url='login')
@never_cache
def authority_view_stray_dog_alerts(request):

    alerts = StrayDogAlert.objects.all().order_by('-id')

    return render(request,'authority_view_stray_dog_alerts.html',{
        'alerts':alerts
    })


@login_required(login_url='login')
def authority_view_cameras(request):

    cameras = Camera.objects.all()

    return render(
        request,
        "authority_view_cameras.html",
        {"cameras": cameras}
    )



from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.conf import settings
import cv2
import os
import time
from datetime import datetime

from .face_detection import process_frame
from .models import UnauthorizedEntry, Camera


camera = None
camera_running = False


@login_required(login_url='login')
def authority_view_unauthorized_entries(request, cam_id):

    global camera, camera_running

    cam = Camera.objects.get(id=cam_id)

    if request.GET.get("action") == "start":

        camera = cv2.VideoCapture(0)
        camera_running = True

        capture_start = None
        captured_images = 0
        session_folder = None
        folder = None

        CAPTURE_DURATION = 6
        MAX_IMAGES = 10

        def generate_frames():

            nonlocal capture_start, captured_images, session_folder, folder
            global camera_running

            while camera_running:

                success, frame = camera.read()
                if not success:
                    break

                processed_frame, detections = process_frame(frame)

                for det in detections:

                    if not det['recognized']:

                        if capture_start is None:

                            capture_start = time.time()
                            captured_images = 0

                            session_folder = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                            folder = os.path.join(
                                settings.MEDIA_ROOT,
                                "unauthorized_faces",
                                session_folder
                            )

                            os.makedirs(folder, exist_ok=True)

                        if time.time() - capture_start <= CAPTURE_DURATION:

                            if captured_images < MAX_IMAGES:

                                x1, y1, x2, y2 = det['box']
                                face = frame[y1:y2, x1:x2]

                                filename = f"{captured_images}.jpg"

                                save_path = os.path.join(folder, filename)

                                cv2.imwrite(save_path, face)

                                if captured_images == 0:
                                    UnauthorizedEntry.objects.create(
                                        camera=cam,
                                        image=f"unauthorized_faces/{session_folder}/{filename}",
                                        detected_time=str(datetime.now())
                                    )

                                captured_images += 1

                        else:
                            capture_start = None

                ret, buffer = cv2.imencode('.jpg', processed_frame)
                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            if camera:
                camera.release()

        return StreamingHttpResponse(
            generate_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )

    if request.GET.get("action") == "stop":

        camera_running = False

        if camera:
            camera.release()

    entries = UnauthorizedEntry.objects.filter(camera=cam).order_by('-id')

    data = []

    for entry in entries:

        folder_path = os.path.dirname(entry.image.path)

        images = []

        if os.path.exists(folder_path):

            for file in sorted(os.listdir(folder_path)):

                images.append(
                    f"/media/unauthorized_faces/{os.path.basename(folder_path)}/{file}"
                )

        data.append({
            "entry": entry,
            "images": images
        })

    return render(
        request,
        "authority_view_unauthorized_entries.html",
        {
            "entries": data,
            "camera": cam
        }
    )


@login_required(login_url='login')
@never_cache
@csrf_exempt
def authority_change_password(request):

    if request.method == 'POST':

        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = request.user   # get logged-in user

        if not user.check_password(old_password):
            messages.error(request,'Old password is incorrect')
            return redirect('authority_change_password')

        if new_password != confirm_password:
            messages.error(request,'Passwords do not match')
            return redirect('authority_change_password')

        user.set_password(new_password)
        user.save()


        messages.success(request,'Password changed successfully')
        return redirect('authority_change_password')

    return render(request,'authority_change_password.html')




@login_required(login_url='login')
@never_cache
def authority_view_worker_request_history(request, wid):

    requests = WorkerRequest.objects.filter(WORKER_id=wid)

    return render(
        request,
        'authority_view_worker_request_history.html',
        {'requests': requests}
    )


@login_required(login_url='login')
@never_cache
def authority_view_emergency_alerts(request):

    alerts = EmergencyAlert.objects.all().order_by('-date')

    return render(
        request,
        'authority_view_emergency_alerts.html',
        {'alerts': alerts}
    )


@login_required(login_url='login')
@never_cache
def admin_view_emergency_alerts(request):

    alerts = EmergencyAlert.objects.all().order_by('-date')

    return render(
        request,
        'admin_view_emergency_alerts.html',
        {'alerts': alerts}
    )

# ================= resident ============================================================================






@csrf_exempt
def login_app(request):
    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid username or password'})

        if user.groups.filter(name='resident').exists():
            resident = Resident.objects.filter(USER=user).first()
            if resident and resident.status == 'approved':
                return JsonResponse({
                    'status': 'ok',
                    'lid': user.id,
                    'group': 'resident'
                })

            return JsonResponse({'status': 'error', 'message': 'Resident not approved'})

        elif user.groups.filter(name='worker').exists():
            worker = Worker.objects.filter(USER=user).first()
            if worker and worker.status == 'approved':
                return JsonResponse({
                    'status': 'ok',
                    'lid': user.id,
                    'group': 'worker'
                })

            return JsonResponse({'status': 'error', 'message': 'Worker not approved'})

        return JsonResponse({'status': 'error', 'message': 'User not allowed'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})



# ======================= resident ===========================================================


@csrf_exempt
def resident_register(request):
    if request.method == 'POST':


        username = request.POST['username']
        password = request.POST['password']
        name = request.POST['name']
        gender = request.POST['gender']
        dob = request.POST['dob']
        phone = request.POST['phone']
        email = request.POST['email']
        house_number = request.POST['house_number']
        latitude = request.POST['latitude']
        longitude = request.POST['longitude']

        photo1 = request.FILES['photo1']
        photo2 = request.FILES.get('photo2')
        photo3 = request.FILES.get('photo3')

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already taken'})

        user = User.objects.create_user(username=username, password=password)

        group = Group.objects.get(name='resident')
        user.groups.add(group)
        user.save()

        resident = Resident.objects.create(
            USER=user,
            photo1=photo1,
            name=name,
            gender=gender,
            dob=dob,
            phone=phone,
            email=email,
            house_number=house_number,
            latitude=latitude,
            longitude=longitude
        )

        import os
        from django.conf import settings

        training_base = os.path.join(settings.MEDIA_ROOT, "resident_training")
        resident_folder = os.path.join(training_base, f"resident_{resident.id}")
        os.makedirs(resident_folder, exist_ok=True)

        photo_paths = []

        if photo1:
            path1 = os.path.join(resident_folder, "photo1.jpg")
            with open(path1, 'wb+') as f:
                for chunk in photo1.chunks():
                    f.write(chunk)
            photo_paths.append(path1)

        if photo2:
            path2 = os.path.join(resident_folder, "photo2.jpg")
            with open(path2, 'wb+') as f:
                for chunk in photo2.chunks():
                    f.write(chunk)
            photo_paths.append(path2)

        if photo3:
            path3 = os.path.join(resident_folder, "photo3.jpg")
            with open(path3, 'wb+') as f:
                for chunk in photo3.chunks():
                    f.write(chunk)
            photo_paths.append(path3)

        print("TRAINING STARTED FOR RESIDENT:", resident.id)
        print("PHOTO PATHS:", photo_paths)

        train_face_recognition(
            person_id=resident.id,
            category='resident',
            photo_paths=photo_paths
        )

        return JsonResponse({'status': 'ok', 'message': 'Registration successful'})

    return JsonResponse({'status': 'error'})



@csrf_exempt
def resident_profile(request):
    if request.method == 'POST':
        lid = request.POST.get('lid')

        user = User.objects.get(id=lid)
        profile = Resident.objects.get(USER=user)

        return JsonResponse({
            'status': 'ok',
            'name': profile.name,
            'gender': profile.gender,
            'dob': profile.dob,
            'phone': profile.phone,
            'email': profile.email,
            'house_number': profile.house_number,
            'latitude': profile.latitude,
            'longitude': profile.longitude,
            'photo1': profile.photo1.url if profile.photo1 else '',
            'status_value': profile.status,
        })

    return JsonResponse({'status': 'error'})


@csrf_exempt
def resident_editprofile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})

    lid = request.POST.get('lid')

    user = User.objects.get(id=lid)
    profile = Resident.objects.get(USER=user)

    profile.name = request.POST.get('name', profile.name)
    profile.gender = request.POST.get('gender', profile.gender)
    profile.dob = request.POST.get('dob', profile.dob)
    profile.phone = request.POST.get('phone', profile.phone)
    profile.email = request.POST.get('email', profile.email)
    profile.house_number = request.POST.get('house_number', profile.house_number)
    profile.latitude = request.POST.get('latitude', profile.latitude)
    profile.longitude = request.POST.get('longitude', profile.longitude)

    if "photo1" in request.FILES:
        profile.photo1 = request.FILES["photo1"]

    profile.save()

    return JsonResponse({
        'status': 'ok',
        'message': 'Resident profile updated successfully'
    })




@csrf_exempt
def resident_add_familymember(request):
    if request.method == 'POST':

        lid = request.POST.get('lid')

        name = request.POST.get('name')
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        relationship = request.POST.get('relationship')
        phone = request.POST.get('phone')

        photo1 = request.FILES['photo1']
        photo2 = request.FILES.get('photo2')
        photo3 = request.FILES.get('photo3')

        user = User.objects.get(id=lid)
        resident = Resident.objects.get(USER=user)

        family = FamilyMember.objects.create(
            RESIDENT=resident,
            photo1=photo1,
            name=name,
            gender=gender,
            age=age,
            relationship=relationship,
            phone=phone
        )

        import os
        from django.conf import settings

        training_base = os.path.join(settings.MEDIA_ROOT, "familymember_training")
        member_folder = os.path.join(training_base, f"familymember_{family.id}")

        os.makedirs(member_folder, exist_ok=True)

        photo_paths = []

        if photo1:
            path1 = os.path.join(member_folder, "photo1.jpg")
            with open(path1, 'wb+') as f:
                for chunk in photo1.chunks():
                    f.write(chunk)
            photo_paths.append(path1)

        if photo2:
            path2 = os.path.join(member_folder, "photo2.jpg")
            with open(path2, 'wb+') as f:
                for chunk in photo2.chunks():
                    f.write(chunk)
            photo_paths.append(path2)

        if photo3:
            path3 = os.path.join(member_folder, "photo3.jpg")
            with open(path3, 'wb+') as f:
                for chunk in photo3.chunks():
                    f.write(chunk)
            photo_paths.append(path3)

        print("TRAINING STARTED FOR FAMILY MEMBER:", family.id)
        print("PHOTO PATHS:", photo_paths)

        train_face_recognition(
            person_id=family.id,
            category='familymember',
            photo_paths=photo_paths
        )

        return JsonResponse({
            'status': 'ok',
            'message': 'Family member added successfully'
        })

    return JsonResponse({'status': 'error'})






@csrf_exempt
def resident_view_familymembers(request):
    if request.method == 'POST':

        lid = request.POST.get('lid')

        user = User.objects.get(id=lid)
        resident = Resident.objects.get(USER=user)

        members = FamilyMember.objects.filter(RESIDENT=resident)

        data = []

        for m in members:
            data.append({
                'id': m.id,
                'name': m.name,
                'gender': m.gender,
                'age': m.age,
                'relationship': m.relationship,
                'phone': m.phone,
                'photo1': m.photo1.url if m.photo1 else ''
            })

        return JsonResponse({
            'status': 'ok',
            'data': data
        })

    return JsonResponse({'status': 'error'})



@csrf_exempt
def resident_edit_familymember(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})

    fid = request.POST.get('fid')

    member = FamilyMember.objects.get(id=fid)

    member.name = request.POST.get('name', member.name)
    member.gender = request.POST.get('gender', member.gender)
    member.age = request.POST.get('age', member.age)
    member.relationship = request.POST.get('relationship', member.relationship)
    member.phone = request.POST.get('phone', member.phone)

    if "photo1" in request.FILES:
        member.photo1 = request.FILES["photo1"]

    member.save()

    return JsonResponse({
        'status': 'ok',
        'message': 'Family member updated successfully'
    })




@csrf_exempt
def resident_delete_familymember(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})

    fid = request.POST.get('fid')

    member = FamilyMember.objects.get(id=fid)
    member.delete()

    return JsonResponse({
        'status': 'ok',
        'message': 'Family member deleted successfully'
    })







@csrf_exempt
def resident_send_complaint(request):

    if request.method == 'GET':
        authorities = Authority.objects.all()
        data = [{'id': i.id, 'name': i.name} for i in authorities]
        return JsonResponse({'status': 'ok', 'authorities': data})

    if request.method == 'POST':
        lid = request.POST.get('lid')
        authority_id = request.POST.get('authority_id')
        complaint = request.POST.get('complaint')

        user = User.objects.get(id=lid)
        resident = Resident.objects.get(USER=user)
        authority = Authority.objects.get(id=authority_id)

        Complaint.objects.create(
            sender=resident,
            receiver=authority,
            complaint=complaint,
            complaint_date=str(datetime.now().date()),
            status='pending'
        )

        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'error'})





@csrf_exempt
def resident_view_complaints(request):

    lid = request.POST.get('lid')

    user = User.objects.get(id=lid)
    resident = Resident.objects.get(USER=user)

    complaints = Complaint.objects.filter(sender=resident).order_by('-complaint_date')

    data = []
    for i in complaints:
        data.append({
            'authority': i.receiver.name,
            'complaint': i.complaint,
            'reply': i.reply,
            'date': i.complaint_date,
            'status': i.status
        })

    return JsonResponse({'status': 'ok', 'data': data})





@csrf_exempt
def resident_view_workers(request):

    lid = request.POST.get('lid')

    user = User.objects.get(id=lid)
    resident = Resident.objects.get(USER=user)

    workers = Worker.objects.filter(status='approved')

    data = []

    for w in workers:

        req = WorkerRequest.objects.filter(
            RESIDENT=resident,
            WORKER=w
        ).order_by('-id').first()

        if req:
            status = req.status
        else:
            status = "not_requested"

        data.append({
            'worker_id': w.id,
            'name': w.name,
            'phone': w.phone,
            'email': w.email,
            'category': w.category.category_name,
            'address': w.address,
            'photo': w.photo1.url if w.photo1 else '',
            'status': status
        })

    return JsonResponse({'status': 'ok', 'data': data})


from datetime import datetime

@csrf_exempt
def resident_send_worker_request(request):

    lid = request.POST.get('lid')
    worker_id = request.POST.get('worker_id')

    user = User.objects.get(id=lid)
    resident = Resident.objects.get(USER=user)

    worker = Worker.objects.get(id=worker_id)

    check = WorkerRequest.objects.filter(
        RESIDENT=resident,
        WORKER=worker,
        status='pending'
    )

    if check.exists():
        return JsonResponse({'status': 'already_requested'})

    WorkerRequest.objects.create(
        RESIDENT=resident,
        WORKER=worker,
        status='pending',
        date=str(datetime.now().date())
    )

    return JsonResponse({'status': 'ok'})







@csrf_exempt
def emergency_alert(request):

    if request.method == 'POST':

        lid = request.POST.get('lid')
        alert_type = request.POST.get('alert_type')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        user = User.objects.get(id=lid)
        resident = Resident.objects.get(USER=user)

        EmergencyAlert.objects.create(
            RESIDENT=resident,
            alert_type=alert_type,
            latitude=latitude,
            longitude=longitude,
            date=str(datetime.now())
        )

        return JsonResponse({
            'status': 'ok',
            'message': 'Emergency alert sent'
        })

    return JsonResponse({'status': 'error'})





@csrf_exempt
def send_stray_dog_alert(request):
    if request.method == "POST":
        lid = request.POST.get("lid")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        description = request.POST.get("description")
        photo = request.FILES.get("photo")

        user = User.objects.get(id=lid)
        resident = Resident.objects.get(USER=user)

        StrayDogAlert.objects.create(
            RESIDENT=resident,
            latitude=latitude,
            longitude=longitude,
            description=description,
            photo=photo
        )

        return JsonResponse({
            "status": "ok",
            "message": "Stray dog alert sent successfully"
        })

@csrf_exempt
def view_stray_dog_alerts(request):
    alerts = StrayDogAlert.objects.all().order_by('-date')

    data = []
    for i in alerts:
        data.append({
            "id": i.id,
            "resident": i.RESIDENT.name,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "description": i.description,
            "photo": request.build_absolute_uri(i.photo.url) if i.photo else "",
            "date": i.date.strftime("%Y-%m-%d %H:%M")
        })

    return JsonResponse({
        "status": "ok",
        "data": data
    })

@csrf_exempt
def delete_stray_dog_alert(request):
    if request.method == "POST":
        aid = request.POST.get("aid")

        StrayDogAlert.objects.filter(id=aid).delete()

        return JsonResponse({
            "status": "ok"
        })
# ================================ worker ===================================================


@csrf_exempt
def worker_register(request):
    if request.method == 'POST':


        username = request.POST['username']
        password = request.POST['password']
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        category_id = request.POST['category']
        address = request.POST['address']

        photo1 = request.FILES['photo1']
        photo2 = request.FILES.get('photo2')
        photo3 = request.FILES.get('photo3')
        id_proof = request.FILES['id_proof']

        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already taken'})

        user = User.objects.create_user(username=username, password=password)

        group = Group.objects.get(name='worker')
        user.groups.add(group)
        user.save()

        category = Category.objects.get(id=category_id)

        worker = Worker.objects.create(
            USER=user,
            photo1=photo1,
            name=name,
            email=email,
            phone=phone,
            category=category,
            address=address,
            id_proof=id_proof
        )

        import os
        from django.conf import settings

        training_base = os.path.join(settings.MEDIA_ROOT, "worker_training")
        worker_folder = os.path.join(training_base, f"worker_{worker.id}")

        os.makedirs(worker_folder, exist_ok=True)

        photo_paths = []

        if photo1:
            path1 = os.path.join(worker_folder, "photo1.jpg")
            with open(path1, 'wb+') as f:
                for chunk in photo1.chunks():
                    f.write(chunk)
            photo_paths.append(path1)

        if photo2:
            path2 = os.path.join(worker_folder, "photo2.jpg")
            with open(path2, 'wb+') as f:
                for chunk in photo2.chunks():
                    f.write(chunk)
            photo_paths.append(path2)

        if photo3:
            path3 = os.path.join(worker_folder, "photo3.jpg")
            with open(path3, 'wb+') as f:
                for chunk in photo3.chunks():
                    f.write(chunk)
            photo_paths.append(path3)

        print("TRAINING STARTED FOR WORKER:", worker.id)
        print("PHOTO PATHS:", photo_paths)

        train_face_recognition(
            person_id=worker.id,
            category='worker',
            photo_paths=photo_paths
        )

        return JsonResponse({'status': 'ok', 'message': 'Registration successful'})

    return JsonResponse({'status': 'error'})




@csrf_exempt
def worker_get_categories(request):

    # print("===== API CALLED =====")
    # print("Request Method:", request.method)
    # print("Full URL:", request.build_absolute_uri())
    # print("Path:", request.path)
    # print("======================")

    categories = Category.objects.all()

    data = []
    for c in categories:
        data.append({
            'id': c.id,
            'category_name': c.category_name
        })

    return JsonResponse({
        'status': 'ok',
        'categories': data
    })


@csrf_exempt
def worker_profile(request):
    if request.method == 'POST':
        lid = request.POST.get('lid')

        user = User.objects.get(id=lid)
        profile = Worker.objects.get(USER=user)

        return JsonResponse({
            'status': 'ok',
            'name': profile.name,
            'email': profile.email,
            'phone': profile.phone,
            'category': profile.category.category_name,
            'address': profile.address,
            'photo1': profile.photo1.url if profile.photo1 else '',
            'id_proof': profile.id_proof.url if profile.id_proof else '',
            'status_value': profile.status,
        })

    return JsonResponse({'status': 'error'})


@csrf_exempt
def worker_editprofile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})

    lid = request.POST.get('lid')

    user = User.objects.get(id=lid)
    profile = Worker.objects.get(USER=user)

    profile.name = request.POST.get('name', profile.name)
    profile.email = request.POST.get('email', profile.email)
    profile.phone = request.POST.get('phone', profile.phone)
    profile.address = request.POST.get('address', profile.address)

    if "photo1" in request.FILES:
        profile.photo1 = request.FILES["photo1"]

    if "id_proof" in request.FILES:
        profile.id_proof = request.FILES["id_proof"]

    profile.save()

    return JsonResponse({
        'status': 'ok',
        'message': 'Worker profile updated successfully'
    })




@csrf_exempt
def worker_view_requests(request):

    lid = request.POST.get('lid')

    user = User.objects.get(id=lid)
    worker = Worker.objects.get(USER=user)

    requests = WorkerRequest.objects.filter(WORKER=worker)

    data = []

    for i in requests:
        data.append({
            "id": i.id,
            "resident_name": i.RESIDENT.name,
            "resident_phone": i.RESIDENT.phone,
            "house_number": i.RESIDENT.house_number,
            "latitude": i.RESIDENT.latitude,
            "longitude": i.RESIDENT.longitude,
            "date": i.date,
            "status": i.status
        })

    return JsonResponse({
        "status": "ok",
        "data": data
    })



@csrf_exempt
def worker_accept_request(request):

    rid = request.POST.get('rid')

    req = WorkerRequest.objects.get(id=rid)
    req.status = "accepted"
    req.save()

    return JsonResponse({
        "status": "ok"
    })



@csrf_exempt
def worker_reject_request(request):

    rid = request.POST.get('rid')

    req = WorkerRequest.objects.get(id=rid)
    req.status = "rejected"
    req.save()

    return JsonResponse({
        "status": "ok"
    })




# ===================================== chat =============================================================================

from django.db.models import Q
from .toxic_detector import detect_toxic_comment
from datetime import datetime

def resident_view_authorities(request):

    lid = request.GET.get("lid")

    authorities = Authority.objects.all()

    data = []

    for i in authorities:

        last_seen = request.GET.get(f"last_seen_{i.USER.id}", 0)

        photo = ""
        if i.photo1:
            photo = request.build_absolute_uri(i.photo1.url)

        unread = Chat.objects.filter(
            sender=i.USER,
            receiver_id=lid,
            id__gt=last_seen
        ).count()

        data.append({
            "id": i.USER.id,
            "name": i.name,
            "photo": photo,
            "unread": unread
        })

    return JsonResponse({"status": "ok", "data": data})

@csrf_exempt
def resident_send_chat(request):

    from_id = request.POST.get("from_id")
    to_id = request.POST.get("to_id")
    message = request.POST.get("message")

    if not message or message.strip() == "":
        return JsonResponse({"status": "error", "message": "Message cannot be empty"})

    sender = User.objects.get(id=from_id)
    receiver = User.objects.get(id=to_id)

    safe_words = ["hi", "hello", "helo", "heloo", "hey"]

    if message.lower() in safe_words:
        result = "Non-Toxic"
        confidence = 1.0
    else:
        result, confidence = detect_toxic_comment(message)

    hate_flag = False
    if result in ["Hate Speech", "Offensive"] and confidence > 0.90:
        hate_flag = True

    print("\n💬 New Chat Message", flush=True)
    print("Message:", message, flush=True)
    print("Prediction:", result, flush=True)
    print("Confidence:", round(confidence, 4), flush=True)
    print("Flagged:", hate_flag, flush=True)
    print("-" * 50, flush=True)

    Chat.objects.create(
        sender=sender,
        receiver=receiver,
        message=message,
        hate_speech_flag=hate_flag,
        date=str(datetime.now().date())
    )

    return JsonResponse({"status": "ok"})


def resident_view_chat(request):

    from_id = request.POST.get("from_id")
    to_id = request.POST.get("to_id")

    chats = Chat.objects.filter(
        Q(sender_id=from_id, receiver_id=to_id) |
        Q(sender_id=to_id, receiver_id=from_id)
    ).order_by("id")

    data = []

    for i in chats:
        data.append({
            "id": i.id,
            "message": i.message,
            "from": i.sender.id,
            "to": i.receiver.id,
            "date": i.date,
            "toxic": i.hate_speech_flag
        })

    return JsonResponse({"status": "ok", "data": data})





def authority_view_approved_residents(request):

    authority_user = request.user

    residents = Resident.objects.filter(status="approved")

    data = []

    for r in residents:

        last_seen = request.session.get(f"last_seen_{r.USER.id}", 0)

        unread = Chat.objects.filter(
            sender=r.USER,
            receiver=authority_user,
            id__gt=last_seen
        ).count()

        data.append({
            "resident": r,
            "unread": unread
        })

    return render(request, "authority_view_approved_residents.html", {
        "residents": data
    })


@csrf_exempt
def authority_send_chat(request):

    sender = request.user
    to_id = request.POST.get("to_id")
    message = request.POST.get("message")

    if not message or message.strip() == "":
        return JsonResponse({"status": "error", "message": "Message cannot be empty"})

    receiver = User.objects.get(id=to_id)

    safe_words = ["hi", "hello", "helo", "heloo", "hey"]

    if message.lower() in safe_words:
        result = "Non-Toxic"
        confidence = 1.0
    else:
        result, confidence = detect_toxic_comment(message)

    hate_flag = False
    if result in ["Hate Speech", "Offensive"] and confidence > 0.70:
        hate_flag = True

    # ----- PRINT IN TERMINAL -----
    print("\n💬 Authority Chat Message", flush=True)
    print("Sender:", sender.username, flush=True)
    print("Receiver ID:", to_id, flush=True)
    print("Message:", message, flush=True)
    print("Prediction:", result, flush=True)
    print("Confidence:", round(confidence, 4), flush=True)
    print("Flagged:", hate_flag, flush=True)
    print("-" * 50, flush=True)
    # -----------------------------

    Chat.objects.create(
        sender=sender,
        receiver=receiver,
        message=message,
        hate_speech_flag=hate_flag,
        date=str(datetime.now().date())
    )

    return JsonResponse({"status": "ok"})


def authority_view_chat(request):

    from_id = request.user.id
    to_id = request.POST.get("to_id")

    chats = Chat.objects.filter(
        Q(sender_id=from_id, receiver_id=to_id) |
        Q(sender_id=to_id, receiver_id=from_id)
    ).order_by("id")

    # mark last seen (moved from deleted authority_chat_page)
    last_chat = chats.last()
    if last_chat:
        request.session[f"last_seen_{to_id}"] = last_chat.id

    data = []

    for i in chats:
        data.append({
            "id": i.id,
            "message": i.message,
            "from": i.sender.id,
            "to": i.receiver.id,
            "date": i.date,
            "toxic": i.hate_speech_flag
        })

    return JsonResponse({"status": "ok", "data": data})