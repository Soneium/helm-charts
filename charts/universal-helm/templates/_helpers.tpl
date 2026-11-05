{{/*
Expand the name of the chart.
*/}}
{{- define "general.name" -}}
{{- default .Chart.Name .Values.global.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "general.sa_name" -}}
{{- default (include "general.name" .) .Values.global.serviceAccount.name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "general.fullname" -}}
{{- if .Values.global.fullnameOverride }}
{{- .Values.global.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.global.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "general.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "general.labels" -}}
helm.sh/chart: {{ include "general.chart" . }}
{{ include "general.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "general.selectorLabels" -}}
app.kubernetes.io/name: {{ include "general.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Render each Pod volume once, while keeping mounts local to each container. */}}
{{- define "general.volumes" -}}
{{- $definitions := list -}}
{{- if .legacyMounts -}}
{{- range .workload.containers -}}
{{- range .mountConfigMaps -}}
{{- $definitions = append $definitions (dict "configMap" .name) -}}
{{- end -}}
{{- end -}}
{{- range .workload.containers -}}
{{- range .mountSecrets -}}
{{- $definitions = append $definitions (dict "secretName" .name) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- range .workload.containers -}}
{{- $definitions = concat $definitions (default (list) .extraVolumes) -}}
{{- end -}}
{{- with .workload.persistence -}}
{{- $definitions = concat $definitions (default (list) .extraVolumes) -}}
{{- end -}}

{{- $seen := dict -}}
{{- range $definitions -}}
{{- $name := "" -}}
{{- $source := dict -}}
{{- if hasKey . "secretName" -}}
{{- $name = .secretName -}}
{{- $source = dict "secret" (dict "secretName" $name "optional" false) -}}
{{- else if hasKey . "configMap" -}}
{{- $name = .configMap -}}
{{- $source = dict "configMap" (dict "name" $name) -}}
{{- else if hasKey . "persistentVolumeClaim" -}}
{{- $name = .persistentVolumeClaim -}}
{{- $source = dict "persistentVolumeClaim" (dict "claimName" $name) -}}
{{- end -}}
{{- if $name -}}
{{- if hasKey $seen $name -}}
{{- if not (deepEqual (get $seen $name) $source) -}}
{{- fail (printf "conflicting volume sources for %s" $name) -}}
{{- end -}}
{{- else -}}
{{- $_ := set $seen $name $source }}
- name: {{ $name }}
{{ toYaml $source | indent 2 }}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end }}
