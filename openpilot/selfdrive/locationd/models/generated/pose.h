#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3756367949668875994);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_649988038482950581);
void pose_H_mod_fun(double *state, double *out_7975290609355008534);
void pose_f_fun(double *state, double dt, double *out_3747162810741447441);
void pose_F_fun(double *state, double dt, double *out_4622144854708215450);
void pose_h_4(double *state, double *unused, double *out_2034104138300694595);
void pose_H_4(double *state, double *unused, double *out_7221129607300295927);
void pose_h_10(double *state, double *unused, double *out_1561728162162688074);
void pose_H_10(double *state, double *unused, double *out_8343161513752116907);
void pose_h_13(double *state, double *unused, double *out_425557749313340936);
void pose_H_13(double *state, double *unused, double *out_389501601016405002);
void pose_h_14(double *state, double *unused, double *out_6807261625183760659);
void pose_H_14(double *state, double *unused, double *out_3257888750960811398);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}