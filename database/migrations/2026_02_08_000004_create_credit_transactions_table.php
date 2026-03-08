<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('credit_transactions', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id')->index();
            $table->enum('type', ['subscription', 'usage', 'topup']);
            $table->integer('credits');
            $table->string('description')->nullable();
            $table->timestamp('created_at')->useCurrent();
            
            // updated_at not strictly required by user but good practice. 
            // The user only specified created_at.
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('credit_transactions');
    }
};
