{{- define "ai-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ai-platform.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Values.appReleaseName -}}
{{- .Values.appReleaseName | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Values.appReleaseName $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "ai-platform.namespace" -}}
{{- default .Values.appReleaseNamespace .Values.namespace.name -}}
{{- end -}}

{{- define "ai-platform.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "ai-platform.name" . }}
app.kubernetes.io/instance: {{ .Values.appReleaseName }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $key, $value := .Values.commonLabels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end -}}

{{- define "ai-platform.apiName" -}}
{{- printf "%s-api" (include "ai-platform.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ai-platform.webName" -}}
{{- printf "%s-web" (include "ai-platform.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ai-platform.apiServiceAccountName" -}}
{{- if .Values.api.serviceAccount.create -}}
{{- default (include "ai-platform.apiName" .) .Values.api.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.api.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "ai-platform.webServiceAccountName" -}}
{{- if .Values.web.serviceAccount.create -}}
{{- default (include "ai-platform.webName" .) .Values.web.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.web.serviceAccount.name -}}
{{- end -}}
{{- end -}}
