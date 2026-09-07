{{- define "ai-platform-migration.image" -}}
{{- $image := .Values.migration.image -}}
{{- if $image.digest -}}
{{- if not (regexMatch "^sha256:[a-f0-9]{64}$" $image.digest) -}}{{ fail "Migration image digest must be a full sha256" }}{{- end -}}
{{- printf "%s@%s" $image.repository $image.digest -}}
{{- else -}}
{{- if .Values.release.requireDigests -}}{{ fail "Release migration requires an immutable image digest" }}{{- end -}}
{{- printf "%s:%s" $image.repository $image.tag -}}
{{- end -}}
{{- end -}}
