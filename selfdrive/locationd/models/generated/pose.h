#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7562252914855705934);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7624660990393256492);
void pose_H_mod_fun(double *state, double *out_4788463691933235788);
void pose_f_fun(double *state, double dt, double *out_278833928334043643);
void pose_F_fun(double *state, double dt, double *out_4640315684238237796);
void pose_h_4(double *state, double *unused, double *out_5623878395716679644);
void pose_H_4(double *state, double *unused, double *out_2968764966026938927);
void pose_h_10(double *state, double *unused, double *out_1108484870937860123);
void pose_H_10(double *state, double *unused, double *out_562715734289542272);
void pose_h_13(double *state, double *unused, double *out_7517291163150813919);
void pose_H_13(double *state, double *unused, double *out_6181038791359271728);
void pose_h_14(double *state, double *unused, double *out_7591297481791533481);
void pose_H_14(double *state, double *unused, double *out_6932005822366423456);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}