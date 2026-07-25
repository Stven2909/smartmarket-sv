<?php

namespace App\Http\Controllers;
use App\Models\Categoria;

use Illuminate\Http\Request;

class CategoriaController extends Controller
{
    /*
     * GET: /api/categorias
     * Lista simple, que sirve para poblar el filtro del Buscador Universal
     */
    public function index()
    {
        return Categoria::orderBy('nombre')->get();
    }
}
