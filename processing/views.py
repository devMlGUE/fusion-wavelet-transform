# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
from forms import *
from PIL import Image
import matplotlib.image as mpimg
from processing.models import *
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.core.servers.basehttp import FileWrapper
from django.contrib.auth.decorators import login_required
from django.template import loader, Context, RequestContext
from django.contrib.auth import authenticate, login, logout
import jsonpickle
sys.path

#   ############ AUTENTICATION ###############
def auth_view(request):
    email = request.POST.get('email', '')
    password = request.POST.get('password', '')
    user = authenticate(username=email, password=password)
    if user is not None:
        login(request, user)
        profile = User.objects.select_related().get(id=request.user.pk).profile
        uploadFiles = File.objects.filter(
            profile=profile).filter(tipo=1).order_by("-id")[:5]
        procesos = Proceso.objects.filter(profile=profile).order_by("-id")[:5]
        return render(request, 'home.html', {'profile': profile, 'uploadFiles': uploadFiles, 'procesos': procesos})
    else:
        error = 'No se ha podido acceder, intente nuevamente'
        return render(request, 'error.html', {'error': error})


def error_login(request):
    error = 'El ususario o la contraseña son incorrectos'
    return render(request, 'error.html', {'error': error})


def log_in(request):
    return render(request, 'login.html')


def log_out(request):
    logout(request)
    success = 'Ha cerrado sesión satisfactoriamente. Si desdea acceder de nuevo haga clic en el siguiente botón:'
    url_continuar = '/login'
    msg_continuar = 'Acceder a la cuenta'
    return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})


#  ############ REGISTRATION ###############
def register_user(request):
    if request.POST:
        email = request.POST.get('email', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 == password2:
            try:
                if User.objects.filter(username=email):
                    error = 'El usuario ya existe'
                    return render(request, 'error.html', {'error': error})
                else:
                    new_user = User(username=email, email=email)
                    new_user.set_password(password1)
                    new_user.save()
                    new_profile = Profile(user=new_user,
                                          email=email,
                                          firstName=request.POST.get('firstName', ''),
                                          lastName=request.POST.get('lastName', ''),
                                          )
                    new_profile.save()
                    # Agrego los 5 archivos predeterminados al usuario
                    testFiles = File.objects.filter(test=True)
                    for f in testFiles:
                        url_file = f.fileUpload.url
                        new_test_file = File(fileUpload=Django_File(open("%s%s" % (settings.BASE_DIR, url_file))),
                                             description="Archivo de Prueba", profile=new_profile, ext="results", tipo=1)
                        new_test_file.save()
                    success = 'Se ha registrado satisfactoriamente.'
                    url_continuar = '/login'
                    msg_continuar = 'Acceder a la cuenta'
                    return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})
            except:
                error = 'Error al registrar intente de nuevo'
                return render(request, 'error.html', {'error': error})
        else:
            error = 'Las contrasenas no son iguales'
            return render(request, 'error.html', {'error': error})
    else:
        return render(request, 'register.html')


#  ############ FILES ###############

@login_required(login_url='/login/')
def filesubmit(request):
    if request.method == 'POST':
        #  try:
        desc = request.POST.get('description', '')
        tipo_imagen = True if request.POST.get('tipo', '') == "Multiespectral" else False
        user = User.objects.select_related().get(id=request.user.pk)
        p = user.profile
        ext = str(request.FILES['file']).split(".")[-1]
        instance = File(fileUpload=request.FILES[
                        'file'], description=desc, profile=p, ext=ext, tipo=1, tipo_multi=tipo_imagen)
        instance.save()
        outfile = instance.fileUpload.path + ".jpg"
        # Se genera una imagen en formato JPG para poder mostrar en el navegador.
        print outfile
        try:
            im = Image.open(os.path.join(instance.fileUpload.path),mode="r")
            print "Generating jpeg for %s" % instance.fileUpload.path
            im.thumbnail(im.size)
            im.save(outfile, "JPEG", quality=100)
            success = 'El archivo se ha guardado satisfactoriamente.'
        except Exception, e:
            instance.delete()
            return render(request, 'error.html', {'error': e})

        #se obtiene el origen (esquina sup-izq)
        try:
            x1, y1, sizex, sizey = getXY(instance.fileUpload.path)
            instance.x = x1
            instance.y = y1
            instance.cell_size = sizex
            instance.save()
            success = 'El archivo se ha guardado satisfactoriamente.'
        except Exception, e:
            success = 'El archivo se ha guardado satisfactoriamente, pero no se encontró metadatos sobre sus coordenadas.'
        url_continuar = '/files'
        msg_continuar = 'Ver lista de archivos'
        return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})
        #  except Exception as e:
        #    print e
    else:
        return render(request, 'upload.html')


@login_required(login_url='/login/')
def delete_file(request, fileID):
    try:
        file2del = File.objects.get(id=int(fileID))
        profile = ser = User.objects.select_related().get(id=request.user.pk).profile
        if file2del.profile == profile:
            file2del.delete()
            success = 'Se ha eliminado el archivo satisfactoriamente.'
            url_continuar = '/files'
            msg_continuar = 'Ver lista de archivos'
            return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})
        else:
            error = 'Este archivo no le pertenece'
            return render(request, 'error.html', {'error': error})
    except Exception, e:
        return render(request, 'error.html', {'error': e})


@login_required(login_url='/login/')
def show_fileupload(request):
    form = UploadFileForm()
    return render(request, 'fileupload.html', {'form': form})


@login_required(login_url='/login/')
def show_edit_file(request, fileID):
    return render(request, 'show_edit_file.html', {'fileID': fileID})


@login_required(login_url='/login/')
def editfile(request):
    desc = request.POST.get('description', '')
    fileID = request.POST.get('fileid', '')

    try:
        profile = User.objects.select_related().get(id=request.user.pk).profile
        instance = File.objects.get(id=int(fileID))
        instance.description = desc
        instance.save()
        success = 'Se ha editado el archivo satisfactoriamente.'
        url_continuar = '/files'
        msg_continuar = 'Ver lista de archivos'
        return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})
    except Exception, e:
        error = 'No se pudieron guardar los datos'
        return render(request, 'error.html', {'error': error})


#  ############ PAGE RENDER ###############
def home(request):
    if request.user.is_authenticated():
        if request.method == 'POST':
            form = ImagesForm(request.POST)
            if form.is_valid():
                pass# Hago cosas:
        # if a GET (or any other method) we'll create a blank form
        else:
            profile = User.objects.select_related().get(id=request.user.pk).profile
            pan_image_files = File.objects.all().filter(profile=profile).filter(tipo=1).filter(tipo_multi=False)
            mul_image_files = File.objects.all().filter(profile=profile).filter(tipo=1).filter(tipo_multi=True)
            json_pan = '{'
            json_mul = '{'
            for pan in pan_image_files:
                json_pan=json_pan+'\"'+str(pan.fileUpload)+'\":{\"x\":\"'+str(pan.x)+'\",\"y\":\"'+str(pan.y)+'\",\"cell_size\":\"'+str(pan.cell_size)+'\"},';
            json_pan = json_pan[:-1]+'}'
            for mul in mul_image_files:
                json_mul=json_mul+'\"'+str(mul.fileUpload)+'\":{\"x\":\"'+str(mul.x)+'\",\"y\":\"'+str(mul.y)+'\",\"cell_size\":\"'+str(mul.cell_size)+'\"},';
            json_mul = json_mul[:-1]+'}'
            return render(request, 'home.html', {'pan_image_files': pan_image_files, 'mul_image_files': mul_image_files, 'json_pan':json_pan,'json_mul':json_mul})
    else:
        return render(request, 'home.html')


def show_video(request):
    return render(request, 'video.html')


def show_tutorial(request):
    image_data = open('%s/Manuales/ManualUsuarioFUSATIMA.pdf' % settings.BASE_DIR, 'rb').read()
    return HttpResponse(image_data, content_type='application/pdf')


@login_required(login_url='/login/')
def upload_success(request):
    success = 'Se ha subido el archivo satisfactoriamente.'
    return render(request, 'success.html', {'success': success})


@login_required(login_url='/login/')
def show_files(request):
    user = User.objects.select_related().get(id=request.user.pk)
    profile = user.profile
    mul_file_list = File.objects.all().filter(profile=profile).filter(tipo=1).filter(tipo_multi=True).order_by("-id")
    pan_file_list = File.objects.all().filter(profile=profile).filter(tipo=1).filter(tipo_multi=False).order_by("-id")
    return render(request, 'files.html', {'pan_file_list': pan_file_list, 'mul_file_list': mul_file_list})


@login_required(login_url='/login/')
def show_process(request):
    user = User.objects.select_related().get(id=request.user.pk)
    profile = user.profile
    processes = Proceso.objects.all().filter(profile=profile).order_by("-id")
    return render(request, 'processes.html', {'process_list': processes})


@login_required(login_url='/login/')
def show_error_process(request, process_id):
    p = Proceso.objects.get(id=process_id)
    return render(request, 'proccess_error.html', {'p': p})


@login_required(login_url='/login/')
def show_processes(request):
    return render(request, 'show_processes.html')


#  Show standard err and output of process
@login_required(login_url='/login/')
def show_specific_process(request, process_id):
    p = Proceso.objects.get(id=process_id)
    return render(request, 'show_process_info.html', {'p': p})


@login_required(login_url='/login/')
def download_file(request, id_file):
    file_path = File.objects.get(id=id_file).fileUpload.path
    wrapper = FileWrapper(file(file_path))
    filename = file_path.split("/")[-1]
    response = HttpResponse(wrapper, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    response['Content-Length'] = os.path.getsize(file_path)
    print os.path.getsize(file_path)
    print file_path
    return response

########## RUN THE FUSION SCRIPT ################

@login_required(login_url='/login/')
def make_fusion(request):
    #Obtengo las variables dle formulario
    file_mul = request.POST.get('file_mul', '')
    file_pan = request.POST.get('file_pan', '')
    lat_pan = request.POST.get('lat_pan', '')
    lat_mul = request.POST.get('lat_mul', '')
    lon_mul = request.POST.get('lon_mul', '')
    lon_pan = request.POST.get('lon_pan', '')
    nivel = request.POST.get('nivel', '')
    tam_pixel_mul = request.POST.get('tam_pixel_mul', '')
    tam_pixel_pan = request.POST.get('tam_pixel_pan', '')
    diadica_mul = request.POST.get('diadica_mul', '')
    x_mul = float(request.POST.get('x_mul', ''))
    y_mul = float(request.POST.get('y_mul', ''))
    x2_mul = float(request.POST.get('x2_mul', ''))
    y2_mul = float(request.POST.get('y2_mul', ''))
    x_pan = float(request.POST.get('x_pan', ''))
    y_pan = float(request.POST.get('y_pan', ''))
    x2_pan = float(request.POST.get('x2_pan', ''))
    y2_pan = float(request.POST.get('y2_pan', ''))
    #corto ambas imagenes
    file_pan = super_crop(file_pan,x_pan,y_pan,x2_pan,y2_pan)
    file_mul = super_crop(file_mul,x_mul,y_mul,x2_mul,y2_mul)
    # Cambio el tamaño de celda de cada imagen segun su tamaño de pixel y el MCD
    mcd = m_c_d(int(tam_pixel_mul), int(tam_pixel_pan))
    print 'el maximo comun divisor es %s'%mcd
    pan_image = getNewCellSizeImage(file_pan,int(tam_pixel_pan),mcd)
    mul_image = getNewCellSizeImage(file_mul,int(tam_pixel_mul),mcd)
    print 'shape pan_image:%s'%(pan_image.shape,)
    print 'shape mul_image:%s'%(mul_image.shape,)
    # voy bien :D ahora guardo las iamgenes para ver si quedaro bn muahahahha
    newCell_mul_url = '/home/nazkter/Sofware_Develop/fusion_multipan/files/new_cell'+file_mul[2:]
    newCell_pan_url = '/home/nazkter/Sofware_Develop/fusion_multipan/files/new_cell'+file_pan[2:]
    im_pan = Image.fromarray(pan_image)
    im_mul = Image.fromarray(mul_image)
    im_pan.save(newCell_pan_url)
    im_mul.save(newCell_mul_url)
    #plt.imsave(newCell_pan_url,pan_image, cmap=plt.cm.gray)
    #plt.imsave(newCell_mul_url,mul_image)
    ############################################################################
    profile = User.objects.select_related().get(id=request.user.pk).profile    
    f = Fusion(profile=profile)
    f.save()
    f.run(file_pan=newCell_pan_url, file_mul=newCell_mul_url, nivel=nivel)
    success = 'El proceso se ha enviado a ejecución, para ver su estado, consulte la lista de procesos por medio del boton "Procesos" del menú principal o haciendo clic en el siguiente botón:'
    url_continuar = '/process/show'
    msg_continuar = 'Ver lista de procesos'
    return render(request, 'success.html', {'success': success, 'url_continuar': url_continuar, 'msg_continuar': msg_continuar})

########## OTHER SCRIPTS ################
def m_c_d(a, b):
    return a if b == 0 else m_c_d(b, a%b)

def super_crop(file,x1,y1,x2,y2):
    url = '/home/nazkter/Sofware_Develop/fusion_multipan/files'+file[1:]
    img = Image.open(url)
    aux = img.crop((x1, y1, x2, y2))
    crop_url = '/home/nazkter/Sofware_Develop/fusion_multipan/files/crop_'+file[2:]
    aux.save(crop_url)
    return './crop_'+file[2:]

def getNewCellSizeImage(image, cell_size, mcd):
    if cell_size == mcd:
        img = '/home/nazkter/Sofware_Develop/fusion_multipan/files'+image[1:]
        print 'la imagen %s no necesita cambiar el tamao de celda'%(img)
        return plt.imread(img)

    image_origin = plt.imread('/home/nazkter/Sofware_Develop/fusion_multipan/files'+image[1:])
    shape = image_origin.shape
    print shape
    expand = cell_size/mcd # cantidad de celdas nuevas por cada actual
    img_size_x = shape[0] # tamaño de un lado de la imagen
    img_size_y = shape[1] # tamaño de un lado de la imagen
    if shape[2]:
        new_image = np.zeros((img_size_x*expand, img_size_y*expand, shape[2])) # creo una imagen del tamaño de la imagen final
    else:
        new_image = np.zeros((img_size_x*expand, img_size_y*expand)) # creo una imagen del tamaño de la imagen final
    shape = image_origin.shape
    x = 0
    y = 0
    while y < shape[1]:
        while x < shape[0]:
            # tomo cada pixel y lo replico "expand" veces
            pixel = image_origin[x][y]
            #print 'Pixel[%s][%s]:%s'%(x,y,pixel)
            a=0
            b=0
            #if (x*expand+b) < shape[0] and (y*expand+a) < shape[1]:
            while a < expand:
                while b < expand:
                    new_image[x*expand+b][y*expand+a] = pixel
                    b=b+1
                a=a+1
                b=0
            #print 'New image:\n%s'%(new_image,)
            x=x+1
        y=y+1
        x=0
    return new_image


# Devuelve X, Y, tamaño de celda vertical y tamaño de celda horizontal de la imagen
def getXY(input_file):   
    from osgeo import gdal      
    # print type(filetoread)    
    ds = gdal.Open(input_file)    
    width = ds.RasterXSize    
    height = ds.RasterYSize    
    gt = ds.GetGeoTransform()
    band1 = ds.GetRasterBand(1).ReadAsArray()
    minx = gt[0]
    miny = gt[3]    
    maxy = gt[3] + width * gt[4] + height * gt[5]    
    maxx = gt[0] + width * gt[1] + height * gt[2]    

    if not gt is None:
        return int(gt[0]), int(gt[3]), int(gt[1]), int(gt[5])
    else:
        return None