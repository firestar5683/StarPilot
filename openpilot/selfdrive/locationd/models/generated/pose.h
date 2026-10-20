#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6044847391441660522);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5641758511196693149);
void pose_H_mod_fun(double *state, double *out_3649931908543644442);
void pose_f_fun(double *state, double dt, double *out_1050158138610913571);
void pose_F_fun(double *state, double dt, double *out_7004170523943837202);
void pose_h_4(double *state, double *unused, double *out_469880496905936735);
void pose_H_4(double *state, double *unused, double *out_6924153987334593695);
void pose_h_10(double *state, double *unused, double *out_7742792149057052598);
void pose_H_10(double *state, double *unused, double *out_9199083287878354631);
void pose_h_13(double *state, double *unused, double *out_6098920331360951697);
void pose_H_13(double *state, double *unused, double *out_3711880162002260894);
void pose_h_14(double *state, double *unused, double *out_2194294574888024015);
void pose_H_14(double *state, double *unused, double *out_2960913130995109166);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}