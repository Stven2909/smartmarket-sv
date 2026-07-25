<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Nette\Utils\Process;

class Categoria extends Model
{
    protected $fillable = [
        'nombre'
    ];

    //Relaciones
    public function productos()
    {
        return $this->hasMany(Producto::class);
    }
}
