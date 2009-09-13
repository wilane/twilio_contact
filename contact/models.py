from django.db import models
from django.contrib.localflavor.us.models import PhoneNumberField
# Create your models here.

class Enumeration(object):
    """
    A small helper class for more readable enumerations,
    and compatible with Django's choice convention.
    You may just pass the instance of this class as the choices
    argument of model/form fields.

    Example:
        MY_ENUM = Enumeration([
            (100, 'MY_NAME', 'My verbose name'),
            (200, 'MY_AGE', 'My verbose age'),
        ])
        assert MY_ENUM.MY_AGE == 100
        assert MY_ENUM[1] == (200, 'My verbose age')
    """

    def __init__(self, enum_list):
        self.enum_list = [(item[0], item[1]) for item in enum_list]
        self.enum_dict = {}
        for item in enum_list:
            self.enum_dict[item[1]] = item[0]

    def __contains__(self, v):
        return (v in self.enum_list)

    def __len__(self):
        return len(self.enum_list)
    def __getitem__(self, v):
        if isinstance(v, basestring):
            return self.enum_dict[v]
        elif isinstance(v, int):
            return self.enum_list[v]

    def __getattr__(self, name):
        return self.enum_dict[name]

    def __iter__(self):
        return self.enum_list.__iter__()


CallStatus = Enumeration([
    ('0', 'Not Yet Dialed'),
    ('1', 'In Progress'),
    ('2', 'Complete'),
    ('3', 'Failed - Busy'),    
    ('4', 'Failed - Application Error'),
    ('5', 'Failed - No Answer'),
])

class contact(models.Model):
    name = models.CharField("Full name", max_length=128)
    phone = PhoneNumberField("Phone number")
    email = models.EmailField("Email")
    motive = models.TextField("Motive", help_text="What's the motive of your call?")

    vm = models.BooleanField(default=False)
    voicemail = models.URLField(blank=True, null=True, editable=False)
    transcribe = models.TextField(editable=False)

    Sid = models.CharField(max_length=64, editable=False, blank=True, null=True)

    def __unicode__(self):
        return u"%s {<%s>, <%s>}" %(self.name, self.phone, self.email)

    def completed(self):
        return all([(l.Status == "2") for l in self.leg_set.all()])

class leg(models.Model):
    contact = models.ForeignKey('contact')    
    CallSegmentSid = models.CharField(max_length=64, editable=False, blank=True, null=True)
    DateCreated = models.DateTimeField(editable=False, blank=True, null=True)
    DateUpdated = models.DateTimeField(editable=False, blank=True, null=True)
    AccountSid = models.CharField(max_length=64, editable=False, blank=True, null=True)
    Called = models.CharField(max_length=64, editable=False, blank=True, null=True)
    Caller = models.CharField(max_length=64, editable=False, blank=True, null=True)
    PhoneNumberSid = models.CharField(max_length=64, editable=False, blank=True, null=True)
    Status = models.CharField(editable=False, max_length=8, choices=CallStatus, blank=True, null=True)
    StartTime = models.DateTimeField(editable=False, blank=True, null=True)
    EndTime = models.DateTimeField(editable=False, blank=True, null=True)
    Duration = models.FloatField(editable=False, blank=True, null=True)

    Price = models.FloatField(editable=False, blank=True, null=True)

    def __unicode__(self):
        return u"%s - %s" %(self.contact, self.CallSegmentSid)
    
    def _state(self):
        return CallStatus[int(self.Status)][1]

    state = property(_state)
