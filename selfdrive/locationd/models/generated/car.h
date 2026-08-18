#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_395710906661730109);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6370952191766860566);
void car_H_mod_fun(double *state, double *out_8610422609060100183);
void car_f_fun(double *state, double dt, double *out_7209711513462721716);
void car_F_fun(double *state, double dt, double *out_832953036043329844);
void car_h_25(double *state, double *unused, double *out_6217004965884737485);
void car_H_25(double *state, double *unused, double *out_2113399649170070232);
void car_h_24(double *state, double *unused, double *out_724420575405524496);
void car_H_24(double *state, double *unused, double *out_2755415215857636620);
void car_h_30(double *state, double *unused, double *out_5458903881474463195);
void car_H_30(double *state, double *unused, double *out_2414296680957537966);
void car_h_26(double *state, double *unused, double *out_7645972956349057858);
void car_H_26(double *state, double *unused, double *out_1628103669703985992);
void car_h_27(double *state, double *unused, double *out_2579304498381259655);
void car_H_27(double *state, double *unused, double *out_190702609773594749);
void car_h_29(double *state, double *unused, double *out_7986166924574242776);
void car_H_29(double *state, double *unused, double *out_1904065336643145782);
void car_h_28(double *state, double *unused, double *out_3819737019032589491);
void car_H_28(double *state, double *unused, double *out_6986464353712676356);
void car_h_31(double *state, double *unused, double *out_6059818297533608340);
void car_H_31(double *state, double *unused, double *out_2254311771937337468);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}