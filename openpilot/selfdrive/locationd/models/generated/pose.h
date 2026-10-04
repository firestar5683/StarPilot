#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7161146668565307749);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_9192799682543864141);
void pose_H_mod_fun(double *state, double *out_7855275330575582361);
void pose_f_fun(double *state, double dt, double *out_5704836990456063535);
void pose_F_fun(double *state, double dt, double *out_3943621887978734192);
void pose_h_4(double *state, double *unused, double *out_4630127890418963741);
void pose_H_4(double *state, double *unused, double *out_8609436332630294968);
void pose_h_10(double *state, double *unused, double *out_4053444435124290898);
void pose_H_10(double *state, double *unused, double *out_1071649461987014282);
void pose_h_13(double *state, double *unused, double *out_7118410191472981609);
void pose_H_13(double *state, double *unused, double *out_2226676532762555719);
void pose_h_14(double *state, double *unused, double *out_4049122250011499148);
void pose_H_14(double *state, double *unused, double *out_5526647900334922672);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}