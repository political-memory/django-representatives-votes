from django.contrib import admin

from import_parltrack_votes.models import Matching

class NoneMatchingFilter(admin.SimpleListFilter):
    title = 'Representative'
    parameter_name = 'representative'

    def lookups(self, request, model_admin):
        return [('None', 'Unknown')]
    
    def queryset(self, request, queryset):
        if self.value() == 'None':
            return queryset.filter(representative=None)
        else:
            return queryset            


class MatchingAdmin(admin.ModelAdmin):
    list_display = ('mep_name', 'mep_group', 'representative')
    list_filter = (NoneMatchingFilter,)
    
admin.site.register(Matching, MatchingAdmin)
