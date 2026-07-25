<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AliasProducto extends Model
{
    protected $table = 'alias_productos'; //-> para que la tabla si o si se llame asi

    protected $fillable = [
        'producto_id', 'alias', 'origen'
    ];

    //Relacion directa con el modelo de Producto
    public function producto()
    {
        return $this->belongsTo(Producto::class);
    }
}
