import 'package:flutter/material.dart';
import 'package:google_sign_in_web/web_only.dart' as web;

Widget googleButton(BuildContext context, VoidCallback? onPressed) => SizedBox(
      height: 52,
      child: Center(
        child: web.renderButton(
          configuration: web.GSIButtonConfiguration(
            type: web.GSIButtonType.standard,
            theme: Theme.of(context).brightness == Brightness.dark
                ? web.GSIButtonTheme.filledBlack
                : web.GSIButtonTheme.outline,
            size: web.GSIButtonSize.large,
            text: web.GSIButtonText.continueWith,
            shape: web.GSIButtonShape.pill,
            locale: 'fr',
            minimumWidth: 300,
          ),
        ),
      ),
    );
