#import webodt
import shutil
import StringIO
#from webodt.converters import converter
import subprocess
import zipfile

import qrcode
from celery import task
from core.models import CURRENCY_SIGNS, Tip, Wallet
from django.conf import settings
from django.template import Context, RequestContext, Template
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l
from django.utils.translation import activate


def odt_template(fn, ctx, page_size="A4"):
    inp = zipfile.ZipFile(fn, "r" )
    outs = StringIO.StringIO()
    output = zipfile.ZipFile(outs, "a" )
    for zi in inp.filelist:
            out = inp.read(zi.filename)
            if zi.filename == 'content.xml': # waut for the only interesting file
                    # un-escape the quotes (in filters etc.)
                    t = Template(out.replace( '&quot;', '"' ))
                    out = t.render(ctx).encode('utf8')
            if page_size=="US" and zi.filename == 'styles.xml' :
                    t = Template(out.replace( 'style:page-layout-properties fo:page-width="297mm" fo:page-height="210.01mm"', 'style:page-layout-properties fo:page-width="279.4mm" fo:page-height="215.9mm"' ))
                    out = t.render(ctx).encode('utf8')
            output.writestr(zi.filename, out)
    output.close()
    content=outs.getvalue()
    return content

#from celery.task.control import inspect
#i = inspect()
#i.scheduled()
#i.active()

@task #(name='tasks.celery_generate_pdf')
def celery_generate_pdf(wallet):
    activate(wallet.target_language)
    tips = Tip.objects.filter(wallet=wallet).order_by('id')
    ctx = {'wallet':wallet, 'tips':tips}
    ctx['cur_sign'] = CURRENCY_SIGNS[wallet.divide_currency]
    #print "asdff"
    #_startDate = home.home_startdate.strftime('%m/%d/%Y')
    # let's begin
    unique_tmp = '/tmp/w%s.odt'%wallet.id
    shutil.copyfile(settings.WEBODT_TEMPLATE_PATH +"/"+ wallet.template, unique_tmp)
    inpt = zipfile.ZipFile(unique_tmp, "a" )
    text = StringIO.StringIO()
    for tip in tips:
        inpt.writestr("Pictures/%s.png"%tip.id, qrcode_img(tip.get_absolute_url()) )
    manifest = Template( inpt.read( 'META-INF/manifest.xml' ) )
    inpt.writestr("META-INF/manifest.xml", manifest.render( Context(ctx) ))
    inpt.close()
    # fuu
    #template = webodt.ODFTemplate(unique_tmp) #webodt.HTMLTemplate('test.html')
    #document = template.render(Context(ctx))
    document = odt_template(unique_tmp, Context(ctx))
    document_us = odt_template(unique_tmp, Context(ctx), page_size="US")

    #odt
    fn = settings.PROJECT_DIR+"/static/odt/tips-%s.odt"%wallet.key
    f = open(fn,'w')
    f.write(document)
    f.close()

    fn = settings.PROJECT_DIR+"/static/odt/tips-us-%s.odt"%wallet.key
    f = open(fn,'w')
    f.write(document_us)
    f.close()

    #pdf
    s=["unoconv", "-f", "pdf", "-o", settings.PROJECT_DIR+"/static/pdf/tips-%s.pdf"%wallet.key, settings.PROJECT_DIR+"/static/odt/tips-%s.odt"%wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    s=["unoconv", "-f", "pdf", "-o", settings.PROJECT_DIR+"/static/pdf/tips-us-%s.pdf"%wallet.key, settings.PROJECT_DIR+"/static/odt/tips-us-%s.odt"%wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    #png
    s=["convert", "-density", "300", "-trim", settings.PROJECT_DIR+"/static/pdf/tips-%s.pdf"%wallet.key, settings.PROJECT_DIR+"/static/png/tips-%s.png"%wallet.key]
    subprocess.call(s)
    subp = subprocess.Popen(s, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retval = subp.wait()

    return True

def qrcode_img(text):
    img = qrcode.make(text, box_size=2, error_correction=qrcode.ERROR_CORRECT_M)
    output = StringIO.StringIO()
    img.save(output, "PNG")
    c = output.getvalue()
    return c
