import datetime
import logging
from xml.dom import minidom
from email.utils import parsedate_tz, mktime_tz

from django.utils import simplejson
from django.core import serializers
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.mail import send_mail    
from django.shortcuts import render_to_response

from forms import ContactForm
from contact.models import contact, leg

import twilio

account = twilio.Account(settings.ACCOUNT_SID, settings.ACCOUNT_TOKEN)
       
def updateContact(response, ctc):        
    dom = minidom.parseString(response)

    for call in dom.getElementsByTagName("Call"):
        ctc.Sid = call.getElementsByTagName("Sid")[0].childNodes[0].data
        ctc.save()
        if call.getElementsByTagName("CallSegmentSid") and call.getElementsByTagName("CallSegmentSid")[0].hasChildNodes():        
            CallSegmentSid=call.getElementsByTagName("CallSegmentSid")[0].childNodes[0].data
        else:
            # inital call have it empty
            CallSegmentSid =""
        aleg, created = ctc.leg_set.get_or_create(CallSegmentSid=CallSegmentSid)
        for node in ("Called", "Caller", "PhoneNumberSid", "Status", "Duration"):
            if call.getElementsByTagName(node) and call.getElementsByTagName(node)[0].hasChildNodes():
                try:
                    if call.getElementsByTagName(node)[0].childNodes[0].data:
                        setattr(aleg, node, call.getElementsByTagName(node)[0].childNodes[0].data)
                except Exception, e:
                    logging.debug("An exception occured for node %s: %s" %(node, e))
                    
        for node in ("DateCreated", "DateUpdated", "StartTime", "EndTime"):
            if call.getElementsByTagName(node) and call.getElementsByTagName(node)[0].hasChildNodes():
                try:
                    if call.getElementsByTagName(node)[0].childNodes[0].data:
                        date_val = datetime.datetime.utcfromtimestamp(mktime_tz(parsedate_tz(call.getElementsByTagName(node)[0].childNodes[0].data)))
                        setattr(aleg, node, date_val)
                except Exception, e:
                        logging.debug("An exception occured for node %s: %s; Value: %s" %(node, e, parsedate_tz(call.getElementsByTagName(node)[0].childNodes[0].data)))

        aleg.save()
    
def index(request):
    if request.method == 'POST':
        form = ContactForm(request.REQUEST)
        if form.is_valid():
            ctc = form.save(commit=False)
            ctc.vm = False
            ctc.save()
            # Make the call
            d = {
                'Caller' : settings.CALLER_ID,
                'Called' : ctc.phone,
                'Url' : '%s/call/%s' % (settings.BASE_URL, ctc.pk),
                'IfMachine' : 'Continue', 
                }
            response = account.request('/%s/Accounts/%s/Calls' %(settings.API_VERSION, settings.ACCOUNT_SID), 'POST', d)
            
            updateContact(response, ctc)
            return HttpResponseRedirect(reverse('status', args=[ctc.pk]))
    else:
        form = ContactForm()
        
    return render_to_response('index.html', {'form':form})


def call(request, contact_id):
    ctc = contact.objects.get(pk=int(contact_id))
    digits = request.REQUEST.get('Digits', None)
    dialstatus = request.REQUEST.get('DialStatus', None)    
    if digits:
        if digits == '1':
            r = twilio.Response()
            g=r.addDial(action='%s/vmme/%s' %(settings.BASE_URL, ctc.pk))
            g.addNumber(settings.MY_NUMBER,
                        url='%s/bridge/%s' %(settings.BASE_URL, ctc.pk))
            logging.debug("Calling you now with request: %s" %(r,))
            return HttpResponse(r,mimetype="application/xml")
        
        else: # No input or cancel
            # send Hangup and notice to me
            r = twilio.Response()
            r.addHangup()
            return HttpResponse(r,mimetype="application/xml")
        
    if dialstatus and dialstatus.startswith('answered'): # (answered-human, answered-machine, hangup-machine, busy, no-answer, fail)
        r = twilio.Response()
        message ="Hello %s. You've requested to contact me with the following motives: %s" % (ctc.name, ctc.motive)
        prompt = "Please press 1 if you're willing to proceed or 2 if you want to cancel. Note that in both cases, I'll receive a notice."

        r.addSay(message, voice=twilio.Say.MAN,
                 language=twilio.Say.ENGLISH)
        g = r.append(twilio.Gather(numDigits=1))
        g.append(twilio.Say(prompt, voice=twilio.Say.MAN,
                            language=twilio.Say.ENGLISH))
        return HttpResponse(r,mimetype="application/xml")
    else:
        # Let the user know on the status page
        logging.debug('Dialing %s failed with status: %s' %(ctc.phone, dialstatus))
        # Just do this to avoid 500 for not returning an HttpResponse
        r = twilio.Response()
        r.addHangup()
        return HttpResponse(r,mimetype="application/xml")

def bridge(request, contact_id):
    ctc = contact.objects.get(pk=int(contact_id))

    logging.debug(request.raw_post_data)
    digits = request.REQUEST.get('Digits', None)
    if digits:
        if digits == '1':
            r = twilio.Response()
            message ="""Connecting."""
            
            r.addSay(message, voice=twilio.Say.MAN,
                     language=twilio.Say.ENGLISH)
            return HttpResponse(r,mimetype="application/xml") 
        
        else:
            ctc.vm = True
            ctc.save()
            r = twilio.Response()
            r.addHangup()
            return HttpResponse(r,mimetype="application/xml")                

    r = twilio.Response()
    message ="Hello. %s would like to talk to you for the following motive: %s" % (ctc.name, ctc.motive)
    prompt = "Please press 1 if you're willing to take the call or 2 for him to leave a voicemail."

    r.addSay(message, voice=twilio.Say.MAN,
             language=twilio.Say.ENGLISH)
    g = r.append(twilio.Gather(numDigits=1))
    g.append(twilio.Say(prompt, voice=twilio.Say.MAN,
                        language=twilio.Say.ENGLISH))
    
    return HttpResponse(r,mimetype="application/xml")
        
def vmme(request, contact_id):
    ctc = contact.objects.get(pk=int(contact_id))    
    dialstatus = request.REQUEST.get('DialStatus', None)
    logging.debug('The dialstatus of the call to me is: %s' %dialstatus)
    if ctc.vm or not dialstatus.startswith('answered'):
        message ="""It's seems that I'm unavailable, please leave me a voicemail after the beep, and remember to speak
        clearly, in advance, thanks you for your interest."""
        r = twilio.Response()
        r.addSay(message, voice=twilio.Say.MAN,
                 language=twilio.Say.ENGLISH)
            
        r.addRecord(transcribe=True,
                    transcribeCallback='%s/transcribe/%s' %(settings.BASE_URL, ctc.pk),
                    action=reverse('goodbye', args=[ctc.pk]),
                    method="POST",
                    finishOnKey='#',
                    maxLength="30")
        return HttpResponse(r,mimetype="application/xml")
    else:
        r = twilio.Response()
        r.addSay('Goodbye.', voice=twilio.Say.MAN,
                 language=twilio.Say.ENGLISH)
        
        r.addHangup()
        return HttpResponse(r,mimetype="application/xml")            


def transcribe(request, contact_id):
    ctc = contact.objects.get(pk=int(contact_id))    
    if request.REQUEST.get('TranscriptionStatus', None) != "completed":
        # Error
        subject = "Error transcribing voicemail from %s" %(ctc,)
        message = "You have new voicemail, URL: %s" %request.REQUEST.get('RecordingUrl', None)
    else:
        subject = 'New voicemail from %s' %(ctc,)
        message = """%s
Recording URL: %s""" %(request.REQUEST.get('TranscriptionText', None), request.REQUEST.get('RecordingUrl', None))
        ctc.transcribe = request.REQUEST.get('TranscriptionText', None)
        ctc.voicemail = request.REQUEST.get('RecordingUrl', None)
        ctc.save()
        
    send_mail(subject, message, settings.MY_EMAIL,
                  [ctc.email, settings.MY_EMAIL], fail_silently=False)

    return HttpResponse("")


def goodbye(request, contact_id):
    r = twilio.Response()
    r.addSay('Goodbye.', voice=twilio.Say.MAN,
             language=twilio.Say.ENGLISH)
    
    r.addHangup()
    return HttpResponse(r,mimetype="application/xml")


def status(request, contact_id):
    """ Status page that polls the status of the call"""
    return render_to_response('status.html', {'contact': contact.objects.get(pk=int(contact_id)) })

def setSegmentStats(ctc):
    response = account.request('/%s/Accounts/%s/Calls/%s/Segments' %(settings.API_VERSION, settings.ACCOUNT_SID, ctc.Sid), 'GET')
    updateContact(response, ctc)

def setNotifications(ctc):
    response = account.request('/%s/Accounts/%s/Calls/%s/Notifications' %(settings.API_VERSION, settings.ACCOUNT_SID, ctc.Sid), 'GET')

def update(request, contact_id):
    ctc = contact.objects.get(pk=int(contact_id))
    setSegmentStats(ctc)
    response = HttpResponse(mimetype="text/javascript")
    if not ctc.completed():
        qs = ctc.leg_set.none() # or from django.db.models.query import EmptyQuerySet
    else:
        qs = ctc.leg_set.all() 
    serializers.serialize("json", qs, stream=response)
    return response
            
