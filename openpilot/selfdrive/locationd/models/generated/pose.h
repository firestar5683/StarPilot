#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3641871299484350556);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3119284233878604394);
void pose_H_mod_fun(double *state, double *out_2783404226845349256);
void pose_f_fun(double *state, double dt, double *out_5949144455846088993);
void pose_F_fun(double *state, double dt, double *out_7424333812317239085);
void pose_h_4(double *state, double *unused, double *out_8321002018191485436);
void pose_H_4(double *state, double *unused, double *out_5362062883923420523);
void pose_h_10(double *state, double *unused, double *out_2988408482111357830);
void pose_H_10(double *state, double *unused, double *out_298758434706635924);
void pose_h_13(double *state, double *unused, double *out_2632661140725285312);
void pose_H_13(double *state, double *unused, double *out_8574336709255753324);
void pose_h_14(double *state, double *unused, double *out_8641500759550838094);
void pose_H_14(double *state, double *unused, double *out_9121440333446646564);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}