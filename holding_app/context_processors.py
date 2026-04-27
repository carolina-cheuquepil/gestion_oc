def sucursal_actual(request):
    return {
        "usuario_actual_nombre": request.session.get("usuario_nombre"),
        "sucursal_actual_id": request.session.get("sucursal_id"),
        "sucursal_actual_nombre": request.session.get("sucursal_nombre"),
    }
