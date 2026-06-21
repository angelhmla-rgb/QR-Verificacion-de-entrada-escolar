@app.get("/", response_class=HTMLResponse)
async def home(request: Request, clave: str = None):
    CLAVE_SECRETA = "Prefectura2026" # Tú defines esta contraseña
    
    if clave != CLAVE_SECRETA:
        return HTMLResponse(content="""
            <div style="font-family:sans-serif; text-align:center; margin-top:50px;">
                <h2>⚠️ Acceso Restringido</h2>
                <p>Esta página es de uso exclusivo para el personal del CECYTEC en la puerta del plantel.</p>
                <form method="get" action="/">
                    <input type="password" name="clave" placeholder="Contraseña de Prefecto" style="padding:10px; border-radius:5px; border:1px solid #ccc;"><br><br>
                    <button type="submit" style="padding:10px 20px; background:#2c3e50; color:white; border:none; border-radius:5px; cursor:pointer;">Ingresar</button>
                </form>
            </div>
        """, status_code=401)
        
    # Si la clave es correcta, se abre el escáner original
    return templates.TemplateResponse("index.html", {"request": request})
