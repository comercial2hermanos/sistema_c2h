from django import forms
from django.contrib.auth.models import User
from .models import Cliente

# --- FORMULARIO DE CLIENTES ---
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['ruc_cedula', 'nombre', 'telefono', 'direccion', 'es_mayorista'] # <--- Agregado
        widgets = {
            'ruc_cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUC o Cédula'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Completo'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección'}),
            # Checkbox estilizado
            'es_mayorista': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
        }
        labels = {
            'es_mayorista': '¿Es Cliente Especial / Mayorista? (Habilita cambio de precios)'
        }

# --- FORMULARIO DE USUARIOS ---
class UsuarioForm(forms.ModelForm):
    ROLES = [('admin', 'Administrador (Control Total)'), ('colaborador', 'Colaborador (Ventas/Inventario)')]
    rol = forms.ChoiceField(choices=ROLES, widget=forms.Select(attrs={'class': 'form-select'}))
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        required=False,
        help_text="Deja vacío si no quieres cambiar la contraseña."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }