# ENTRYPOINT + CMD juntos:
#   ENTRYPOINT = el programa que SIEMPRE se ejecuta  -> ping -c 3
#   CMD        = argumentos POR DEFECTO              -> localhost
#
#   docker run ping-demo              ->  ping -c 3 localhost
#   docker run ping-demo 8.8.8.8      ->  ping -c 3 8.8.8.8   (lo que escribas sustituye a CMD)
FROM alpine:3.20
ENTRYPOINT ["ping", "-c", "3"]
CMD ["localhost"]
