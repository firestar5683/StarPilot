#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_2897896323809259494);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6584763988727841558);
void pose_H_mod_fun(double *state, double *out_5860240321001220316);
void pose_f_fun(double *state, double dt, double *out_5165064222563725696);
void pose_F_fun(double *state, double dt, double *out_6599370070449602621);
void pose_h_4(double *state, double *unused, double *out_1026954195093436293);
void pose_H_4(double *state, double *unused, double *out_3848307520625342162);
void pose_h_10(double *state, double *unused, double *out_6611596211326426316);
void pose_H_10(double *state, double *unused, double *out_5755249576477243564);
void pose_h_13(double *state, double *unused, double *out_218234667872197902);
void pose_H_13(double *state, double *unused, double *out_636033695293009361);
void pose_h_14(double *state, double *unused, double *out_7359251233175886547);
void pose_H_14(double *state, double *unused, double *out_114933335714142367);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}