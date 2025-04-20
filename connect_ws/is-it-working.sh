./connect-ws.sh \
  --url "wss://xqza8au0ush71rd.studio.eu-central-1.sagemaker.aws/jupyterlab/default/proxy/2719/ws?file=__new__s_acn6gf&session_id=s_fqqic8" \
  --cookie "$(./cookie-pretty.sh --raw <cookie.txt)" \
  --verbose <test-headers.txt
