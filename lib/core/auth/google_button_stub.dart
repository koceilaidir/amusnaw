import 'package:flutter/material.dart';

Widget googleButton(BuildContext context, VoidCallback? onPressed) => OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
      child: const Text('Continuer avec Google'),
    );
